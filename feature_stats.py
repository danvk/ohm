import argparse

import osmium
import osmium.filter

from stats import write_stats


class FileStatsHandler(osmium.SimpleHandler):
    def __init__(self):
        super(FileStatsHandler, self).__init__()
        self.nodes = 0
        self.ways = 0
        self.relations = 0
        self.dated = 0

    def handle_object(self, f):
        if f.tags.get("start_date") or f.tags.get("end_date"):
            self.dated += 1

    def node(self, n):
        self.nodes += 1
        # self.handle_object(n)

    def way(self, w):
        self.ways += 1
        # self.handle_object(w)

    def relation(self, r):
        self.relations += 1
        # self.handle_object(r)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Find elements in an OSM PBF file by name."
    )
    parser.add_argument("osm_file", help="Path to the .osm.pbf file")
    parser.add_argument("--output_dir", default=".")

    args = parser.parse_args()

    handler = FileStatsHandler()
    handler.apply_file(args.osm_file)

    by_type = {
        "num-nodes": handler.nodes,
        "num-ways": handler.ways,
        "num-relations": handler.relations,
        "num-dated": handler.dated,
    }

    write_stats(
        args.output_dir,
        "feature",
        {},
        by_type,
    )


if __name__ == "__main__":
    main()
