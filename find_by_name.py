import argparse
import sys
from typing import Any

import osmium


class NameFinder(osmium.SimpleHandler):
    def __init__(self, search_name: str):
        super(NameFinder, self).__init__()
        self.search_name = search_name

    def node(self, n: Any) -> None:
        if n.tags.get("name") == self.search_name:
            self.print_object("node", n)

    def way(self, w: Any) -> None:
        if w.tags.get("name") == self.search_name:
            self.print_object("way", w)

    def relation(self, r: Any) -> None:
        if r.tags.get("name") == self.search_name:
            self.print_object("relation", r)

    def print_object(self, type_name: str, obj: Any) -> None:
        print(f"Found {type_name}: {obj.id} (version={obj.version})")


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
