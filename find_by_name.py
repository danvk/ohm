import argparse
import re
import sys
from typing import Any

import osmium


class NameFinder(osmium.SimpleHandler):
    def __init__(self, search_name: str):
        super(NameFinder, self).__init__()
        self.search_re = re.compile(search_name)

    def is_match(self, name: str) -> bool:
        return re.match(self.search_re, name) is not None

    def node(self, n: Any) -> None:
        if self.is_match(n.tags.get("name")):
            self.print_object("node", n)

    def way(self, w: Any) -> None:
        if self.is_match(w.tags.get("name")):
            self.print_object("way", w)

    def relation(self, r) -> None:
        if self.is_match(r.tags.get("name")):
            self.print_object("relation", r)

    def print_object(self, type_name: str, obj: Any) -> None:
        print(f"Found {type_name}/{obj.id} {obj.tags.get('name')}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Find elements in an OSM PBF file by name."
    )
    parser.add_argument("osm_file", help="Path to the .osm.pbf file")
    parser.add_argument("name", help="Name to search for")

    args = parser.parse_args()

    print(f"Searching for '{args.name}' in {args.osm_file}...")
    handler = NameFinder(args.name)
    try:
        handler.apply_file(args.osm_file, filters=[osmium.filter.KeyFilter("name")])
    except RuntimeError as e:
        print(f"Error reading file: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
