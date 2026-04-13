import argparse
import re
import sys
from typing import Any

import osmium
import osmium.filter
from osmium.osm import Node, OSMObject, Relation, Way


class NameFinder(osmium.SimpleHandler):
    def __init__(self, search_name: str):
        super(NameFinder, self).__init__()
        self.search_re = re.compile(search_name)

    def is_match(self, o: OSMObject) -> bool:
        name = o.tags.get("name")
        if name and re.match(self.search_re, name):
            return True
        name = o.tags.get("name:en")
        if name and re.match(self.search_re, name):
            return True
        return False

    def node(self, n: Node) -> None:
        if self.is_match(n):
            self.print_object("node", n)

    def way(self, w: Way) -> None:
        if self.is_match(w):
            self.print_object("way", w)

    def relation(self, r: Relation) -> None:
        if self.is_match(r):
            self.print_object("relation", r)

    def print_object(self, type_name: str, obj: Any) -> None:
        name = obj.tags.get("name")
        name_en = obj.tags.get("name:en")
        if name_en == name:
            name_en = None
        print(f"Found {type_name}/{obj.id} {name} {name_en}")


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
