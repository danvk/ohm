import argparse
from collections import Counter, defaultdict
from typing import Any, Callable, Iterable

import osmium
import osmium.filter
from osmium.osm.types import Relation

IGNORE_KEY_PREFIXES = [
    "wikipedia",
    "source",
    "fixme",
]


class DupeCandidateFinder(osmium.SimpleHandler):
    def __init__(self):
        super(DupeCandidateFinder, self).__init__()
        self.name_to_relation = defaultdict[str, list[int]](list)

    def relation(self, r: Relation) -> None:
        name = r.tags.get("name")
        if not name:
            return
        if len(r.members) == 0:
            return  # could remove this, but these are the more problematic ones
        self.name_to_relation[name].append(r.id)


class DupeFinder(osmium.SimpleHandler):
    def __init__(self):
        super(DupeFinder, self).__init__()
        self.key_to_id = defaultdict[tuple, list[int]](list)

    def relation(self, r: Relation) -> None:
        key = relation_key(r)
        self.key_to_id[key].append(r.id)


def relation_key(r: Relation) -> tuple:
    tags = [
        (tag.k, tag.v)
        for tag in r.tags
        if not any(tag.k.startswith(prefix) for prefix in IGNORE_KEY_PREFIXES)
    ]
    tags.sort()
    members = [(m.role, m.type, m.ref) for m in r.members]
    members.sort()
    return (tuple(tags), tuple(members))


def group_by[T](xs: Iterable[T], fn: Callable[[T], Any]) -> dict[Any, T]:
    out = {}
    for x in xs:
        key = fn(x)
        out.setdefault(key, [])
        out[key].append(x)
    return out


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Find elements in an OSM PBF file by name."
    )
    parser.add_argument("osm_file", help="Path to the .osm.pbf file")

    args = parser.parse_args()

    candidate_handler = DupeCandidateFinder()
    candidate_handler.apply_file(
        args.osm_file, filters=[osmium.filter.KeyFilter("name")]
    )

    ids = [
        id
        for ids in candidate_handler.name_to_relation.values()
        for id in ids
        if len(ids) >= 2
    ]

    print("Candidate IDs:", len(ids))
    dupe_handler = DupeFinder()
    # dupe_handler.apply_file(args.osm_file, filters=[osmium.filter.IdFilter(ids)])
    dupe_handler.apply_file(
        args.osm_file, filters=[osmium.filter.IdFilter([2879823, 2879817, 2879806])]
    )

    for k, ids in dupe_handler.key_to_id.items():
        print(f"  {ids}: {k}")

    by_count = Counter[int]()
    total_dupes = 0
    for keys, ids in dupe_handler.key_to_id.items():
        if len(ids) < 2:
            continue
        by_count[len(ids)] += 1
        total_dupes += len(ids) - 1
        name = next(v for k, v in keys[0] if k == "name")
        print(f"{name}: {len(ids)} dupes:")

        for id in ids:
            print(f"  {id} https://www.openhistoricalmap.org/relation/{id}")

    print(f"Total dupes: {total_dupes}")


if __name__ == "__main__":
    main()
