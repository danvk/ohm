import argparse
import itertools
import re
from typing import Iterable

import osmium
import osmium.filter
from osmium.osm import Relation

from dates import Range, overlaps, parse_ohm_date, parse_ohm_range
from stats import write_stats

NAME_RANGE_PAT = r"\(-?\d{3,}--?\d{3,}\)"

type OsmKey = tuple[str, int]  # {"n", "w", "r"} + ID


class DateExtractor(osmium.SimpleHandler):
    def __init__(self):
        super(DateExtractor, self).__init__()
        self.id_to_dates = dict[OsmKey, Range]()
        self.id_to_raw_dates = dict[OsmKey, tuple[str, str]]()
        self.invalid_ids = set[OsmKey]()
        self.invalid = 0
        self.invalid_dates = []
        self.year_names = []
        self.end_no_start = list[OsmKey]()

    def handle_object(self, typ: str, f):
        name = f.tags.get("name")
        if name and re.search(NAME_RANGE_PAT, name):
            self.year_names.append((typ, f.id, name))

        key = (typ, f.id)

        start_date = f.tags.get("start_date")
        end_date = f.tags.get("end_date")
        if start_date:
            start_tup = parse_ohm_date(start_date)
            if not start_tup:
                self.invalid += 1
                self.invalid_dates.append((typ, f.id, start_date))
                self.invalid_ids.add(key)
                return

        if end_date:
            end_tup = parse_ohm_date(end_date)
            if not end_tup:
                self.invalid += 1
                self.invalid_dates.append((typ, f.id, end_date))
                self.invalid_ids.add(key)
                return

        if end_date and not start_date:
            self.end_no_start.append(key)

        self.id_to_dates[key] = parse_ohm_range(start_date, end_date)
        self.id_to_raw_dates[key] = (start_date or "", end_date or "")

    def relation(self, r) -> None:
        self.handle_object("r", r)

    def way(self, w) -> None:
        self.handle_object("w", w)

    def node(self, n) -> None:
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

    def relation(self, r: Relation) -> None:
        if r.tags.get("type") != "chronology":
            return
        self.chronology_count += 1

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
                ("r", r.id, ",".join(f"{typ}/{id}" for typ, id in undated))
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
                    ", ".join(
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
                        ("r", r.id, f"{mtyp}/{mid} ({m_str}) outside {ch_str}")
                    )
                    break


def print_links(ids: Iterable[int]):
    for id in ids:
        print(f"    {id} https://www.openhistoricalmap.org/relation/{id}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Find elements in an OSM PBF file by name."
    )
    parser.add_argument("osm_file", help="Path to the .osm.pbf file")
    parser.add_argument("--output_dir", default=".")

    args = parser.parse_args()

    handler = DateExtractor()
    handler.apply_file(
        args.osm_file, filters=[osmium.filter.KeyFilter("start_date", "end_date")]
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
        },
    )


if __name__ == "__main__":
    main()
