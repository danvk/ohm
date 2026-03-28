import argparse
import itertools
import random
from typing import Iterable

import osmium
import osmium.filter
from osmium.osm import Relation

from dates import parse_ohm_date, parse_ohm_range


class DateExtractor(osmium.SimpleHandler):
    def __init__(self):
        super(DateExtractor, self).__init__()
        self.id_to_dates = dict[int, tuple]()
        self.invalid = 0
        self.invalid_dates = []

    def relation(self, r) -> None:
        start_date = r.tags.get("start_date")
        end_date = r.tags.get("end_date")
        if start_date:
            start_tup = parse_ohm_date(start_date)
            if not start_tup:
                self.invalid += 1
                self.invalid_dates.append(start_date)
                return

        if end_date:
            end_tup = parse_ohm_date(end_date)
            if not end_tup:
                self.invalid += 1
                self.invalid_dates.append(end_date)
                return

        self.id_to_dates[r.id] = parse_ohm_range(start_date, end_date)


def overlaps(a: tuple[float, float], b: tuple[float, float]):
    a1, a2 = a
    b1, b2 = b
    return a1 < b2 and b1 < a2


class ChronologyHandler(osmium.SimpleHandler):
    """Collect type=chronology relations and build a per-member lookup.

    For each member relation, stores a list of
    ``{"id": int, "name": str, "prev": int|None, "next": int|None}`` dicts —
    one entry per chronology the member belongs to.
    """

    def __init__(self, rid_to_dates) -> None:
        super().__init__()
        self.chronology_count = 0
        self.undated_members = []
        self.overlapping_members = []
        self.non_relation_members = []
        self.rid_to_dates = rid_to_dates

    def relation(self, r: Relation) -> None:
        if r.tags.get("type") != "chronology":
            return
        self.chronology_count += 1

        has_undated = False
        has_non_rel = False
        member_dates = []
        for m in r.members:
            if m.type != "r":
                has_non_rel = True
                continue
            dates = self.rid_to_dates.get(m.ref)
            if not dates:
                has_undated = True
                continue
            member_dates.append(dates)

        if has_non_rel:
            self.non_relation_members.append(r.id)
        if has_undated:
            self.undated_members.append(r.id)

        fails = [
            (a, b) for a, b in itertools.combinations(member_dates, 2) if overlaps(a, b)
        ]
        if fails:
            self.overlapping_members.append(r.id)


def print_links(ids: Iterable[int]):
    for id in ids:
        print(f"    {id} https://www.openhistoricalmap.org/relation/{id}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Find elements in an OSM PBF file by name."
    )
    parser.add_argument("osm_file", help="Path to the .osm.pbf file")

    args = parser.parse_args()

    handler = DateExtractor()
    handler.apply_file(
        args.osm_file, filters=[osmium.filter.KeyFilter("start_date", "end_date")]
    )
    print(f"Read {len(handler.id_to_dates)} dated relations.")
    print(f"Found {handler.invalid} invalid dates.")

    print(", ".join(random.sample(handler.invalid_dates, 20)))

    ch = ChronologyHandler(handler.id_to_dates)
    ch.apply_file(
        args.osm_file, filters=[osmium.filter.TagFilter(("type", "chronology"))]
    )

    print(f"n_chronologies: {ch.chronology_count}")
    print(f"  w/ non-relation members: {len(ch.non_relation_members)}")
    print_links(random.sample(ch.non_relation_members, 10))
    print(f"  w/ undated members: {len(ch.undated_members)}")
    print_links(random.sample(ch.undated_members, 10))
    print(f"  w/ overlapping members: {len(ch.overlapping_members)}")
    print_links(random.sample(ch.overlapping_members, 10))


if __name__ == "__main__":
    main()
