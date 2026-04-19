import argparse
import itertools
import re
import time

import edtf as edtf_lib
import osmium
import osmium.filter
from osmium.osm import Node, OSMObject, Relation, Way

from dates import (
    DateTuple,
    Range,
    overlaps,
    parse_ohm_date,
    parse_ohm_range,
    start_of_date,
)
from stats import log_start, write_stats

NAME_RANGE_PAT = r"\(-?\d{3,}--?\d{3,}\)"
# Matches OHM-style ranges written with ".." instead of the EDTF separator "/":
# "1970..1977", "..1970", "1970.."
DOT_DOT_EDTF_PAT = re.compile(r"^(-?\d[\d-]*)?\.\.(-?\d[\d-]*)?$")


def edtf_interval(edtf_str: str) -> tuple[DateTuple, DateTuple] | None:
    """Parse an EDTF string and return (lower, upper) as DateTuples, or None on failure.

    Returns None if the string is not valid EDTF, or if the library cannot compute
    strict bounds (e.g. partially-unspecified dates like '1X00-1X-1X').
    """
    try:
        parsed = edtf_lib.parse_edtf(edtf_str)  # type: ignore[attr-defined]
        lo = parsed.lower_strict()  # type: ignore[attr-defined]
        hi = parsed.upper_strict()  # type: ignore[attr-defined]
    except Exception:
        return None
    lo_tup: DateTuple = (
        (lo.tm_year, lo.tm_mon, lo.tm_mday)
        if isinstance(lo, time.struct_time)
        else (-(10**12), 1, 1)
    )
    hi_tup: DateTuple = (
        (hi.tm_year, hi.tm_mon, hi.tm_mday)
        if isinstance(hi, time.struct_time)
        else (10**12, 1, 1)
    )
    return lo_tup, hi_tup


FAR_FUTURE = 2050

type OsmKey = tuple[str, int]  # {"n", "w", "r"} + ID

# https://github.com/OpenHistoricalMap/iD/blob/7177516c0356f12a35a3a01e8ef599bada802d7f/modules/osm/tags.js#L389-L392
TIMELESS_VALUES = {
    "wood",
    "wetland",
    "beach",
    "cave_entrance",
    "peak",
    "cliff",
    "coastline",
    "tree_row",
    "water",
    "scrub",
    "grassland",
    "heath",
    "bare_rock",
    "glacier",
    "stream",
    "river",
    "pond",
    "basin",
    "lake",
}
TIMELESS_KEYS = {"natural", "waterway", "water"}


class DateExtractor(osmium.SimpleHandler):
    def __init__(self):
        super(DateExtractor, self).__init__()
        self.id_to_dates = dict[OsmKey, Range]()
        self.id_to_raw_dates = dict[OsmKey, tuple[str, str]]()
        self.invalid_ids = set[OsmKey]()
        self.n_invalid = 0
        self.invalid_dates = []
        self.year_names = []
        self.start_after_end = []
        self.end_no_start = list[OsmKey]()
        self.far_future = []
        self.n_timeless = 0
        self.n_edtf = 0
        self.invalid_edtf = []
        self.n_dot_dot_edtf = 0
        self.edtf_mismatch = []

    def handle_object(self, typ: str, f: OSMObject):
        name = f.tags.get("name")
        if name and re.search(NAME_RANGE_PAT, name):
            self.year_names.append((typ, f.id, name))

        key = (typ, f.id)

        start_date = f.tags.get("start_date")
        end_date = f.tags.get("end_date")
        name = f.tags.get("name:en") or f.tags.get("name") or ""
        if start_date:
            start_tup = parse_ohm_date(start_date)
            if not start_tup:
                self.n_invalid += 1
                self.invalid_dates.append((typ, f.id, f"{start_date} {name}"))
                self.invalid_ids.add(key)
                return

        if end_date:
            end_tup = parse_ohm_date(end_date)
            if not end_tup:
                self.n_invalid += 1
                self.invalid_dates.append((typ, f.id, f"{end_date} {name}"))
                self.invalid_ids.add(key)
                return

        if end_date and not start_date:
            is_timeless = False
            for k in TIMELESS_KEYS:
                v = f.tags.get(k)
                if v and v in TIMELESS_KEYS:
                    is_timeless = True
                    break

            if is_timeless:
                self.n_timeless += 1
            else:
                self.end_no_start.append(key)

        range = parse_ohm_range(start_date, end_date)
        if end_date and start_date:
            if range[0] > range[1]:
                self.start_after_end.append(
                    (typ, f.id, f"{start_date} > {end_date} {name}")
                )
        if start_date and range[0][0] > FAR_FUTURE:
            self.far_future.append((typ, f.id, f"{start_date} {name}"))
        if end_date and range[1][0] > FAR_FUTURE:
            self.far_future.append((typ, f.id, f"{end_date} {name}"))

        has_edtf = False
        for plain_tag, edtf_tag in (
            ("start_date", "start_date:edtf"),
            ("end_date", "end_date:edtf"),
        ):
            plain = f.tags.get(plain_tag)
            edtf_str = f.tags.get(edtf_tag)
            if not edtf_str:
                continue
            has_edtf = True
            interval = edtf_interval(edtf_str)
            if interval is None:
                self.invalid_edtf.append((typ, f.id, f"{edtf_tag}={edtf_str} {name}"))
                m = DOT_DOT_EDTF_PAT.match(edtf_str)
                if m and (m.group(1) or m.group(2)):
                    self.n_dot_dot_edtf += 1
                continue
            if plain:
                plain_parsed = parse_ohm_date(plain)
                if plain_parsed:
                    plain_tup = start_of_date(plain_parsed)
                    lo, hi = interval
                    if not (lo <= plain_tup <= hi):
                        self.edtf_mismatch.append(
                            (
                                typ,
                                f.id,
                                f"{plain_tag}={plain} vs {edtf_tag}={edtf_str} {name}",
                            )
                        )

        if has_edtf:
            self.n_edtf += 1

        self.id_to_dates[key] = range
        self.id_to_raw_dates[key] = (start_date or "", end_date or "")

    def relation(self, r: Relation) -> None:
        self.handle_object("r", r)

    def way(self, w: Way) -> None:
        self.handle_object("w", w)

    def node(self, n: Node) -> None:
        self.handle_object("n", n)


def format_range(start: str | None, end: str | None) -> str:
    start = start or ""
    end = end or ""
    sep = (" - " if end else " -") if "-" in f"{start}{end}" else "-"
    return f"{start}{sep}{end}"


class ChronologyHandler(osmium.SimpleHandler):
    """Collect type=chronology relations and build a per-member lookup.

    For each member relation, stores a list of
    ``{"id": int, "name": str, "prev": int|None, "next": int|None}`` dicts —
    one entry per chronology the member belongs to.
    """

    def __init__(
        self,
        tid_to_dates: dict[OsmKey, Range],
        tid_to_raw_dates: dict[OsmKey, tuple[str, str]],
        invalid_tids: set[OsmKey],
    ) -> None:
        super().__init__()
        self.chronology_count = 0
        self.undated_members = []
        self.overlapping_members = []
        self.tid_to_dates = tid_to_dates
        self.tid_to_raw_dates = tid_to_raw_dates
        self.invalid_tids = invalid_tids
        self.date_outside_ranges = []
        self.anonymous_chronologies: list[tuple[str, int, str]] = []

    def relation(self, r: Relation) -> None:
        if r.tags.get("type") != "chronology":
            return
        self.chronology_count += 1
        name = r.tags.get("name:en") or r.tags.get("name") or ""
        name_prefix = f"{name} " if name else ""

        if not name:
            self.anonymous_chronologies.append(("r", r.id, ""))

        undated: list[OsmKey] = []
        member_dates: list[tuple[str, int, Range]] = []
        for m in r.members:
            if (m.type, m.ref) in self.invalid_tids:
                continue

            dates = self.tid_to_dates.get((m.type, m.ref))
            if not dates:
                undated.append((m.type, m.ref))
                continue
            member_dates.append((m.type, m.ref, dates))

        if undated:
            self.undated_members.append(
                (
                    "r",
                    r.id,
                    name_prefix + ",".join(f"{typ}/{id}" for typ, id in undated),
                )
            )

        fails = [
            (a, b)
            for a, b in itertools.combinations(member_dates, 2)
            if overlaps(a[2], b[2])
        ]
        if fails:

            def fmt_member(typ, ref, *_):
                range_str = format_range(
                    *self.tid_to_raw_dates.get((typ, ref), ("", ""))
                )
                return f"{typ}/{ref} ({range_str})"

            self.overlapping_members.append(
                (
                    "r",
                    r.id,
                    name_prefix
                    + ", ".join(
                        fmt_member(*a) + " + " + fmt_member(*b) for a, b in fails[:10]
                    ),
                )
            )

        start_date = r.tags.get("start_date")
        end_date = r.tags.get("end_date")
        if start_date or end_date:
            ch_a, ch_b = parse_ohm_range(start_date, end_date)
            for mtyp, mid, (mem_a, mem_b) in member_dates:
                if mem_a < ch_a or mem_b > ch_b:
                    ch_str = format_range(start_date, end_date)
                    m_str = format_range(
                        *self.tid_to_raw_dates.get((mtyp, mid), ("", ""))
                    )
                    self.date_outside_ranges.append(
                        (
                            "r",
                            r.id,
                            f"{name_prefix}{mtyp}/{mid} ({m_str}) outside {ch_str}",
                        )
                    )
                    break


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Find elements in an OSM PBF file by name."
    )
    parser.add_argument("osm_file", help="Path to the .osm.pbf file")
    parser.add_argument("--output_dir", default=".")

    args = parser.parse_args()
    log_start("chronology")

    handler = DateExtractor()
    handler.apply_file(
        args.osm_file,
        filters=[
            osmium.filter.KeyFilter(
                "start_date", "end_date", "start_date:edtf", "end_date:edtf"
            )
        ],
    )

    n_dated_rels = len(handler.id_to_dates)

    ch = ChronologyHandler(
        handler.id_to_dates, handler.id_to_raw_dates, handler.invalid_ids
    )
    ch.apply_file(
        args.osm_file, filters=[osmium.filter.TagFilter(("type", "chronology"))]
    )

    by_type = {
        "date-invalid": handler.invalid_dates,
        "date-in-name": handler.year_names,
        "date-end-no-start": [(typ, id, "") for typ, id in handler.end_no_start],
        "date-start-after-end": handler.start_after_end,
        "date-far-future": handler.far_future,
        "date-edtf-invalid": handler.invalid_edtf,
        "date-edtf-mismatch": handler.edtf_mismatch,
        "chronology-anonymous": ch.anonymous_chronologies,
        "chronology-undated-member": ch.undated_members,
        "chronology-overlapping-members": ch.overlapping_members,
        "chronology-member-outside-range": ch.date_outside_ranges,
    }

    write_stats(
        args.output_dir,
        "chronology",
        by_type,
        {
            "dated-relations": n_dated_rels,
            "dated-timeless": handler.n_timeless,
            "edtf-features": handler.n_edtf,
            "edtf-invalid-dot-dot": handler.n_dot_dot_edtf,
        },
    )


if __name__ == "__main__":
    main()
