import argparse
import json
import subprocess
import sys

import osmium
import osmium.osm

from stats import write_stats


def count_empty_ways(osm_file: str) -> int:
    fp = osmium.FileProcessor(osm_file, osmium.osm.WAY)
    n_ways = 0
    n_empty_ways = 0
    for obj in fp:
        if not isinstance(obj, osmium.osm.Way):
            continue
        n_ways += 1
        if len(obj.nodes) == 0:
            n_empty_ways += 1

    sys.stderr.write(f"{osm_file}: {n_ways=} {n_empty_ways=}\n")
    return n_empty_ways


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Find elements in an OSM PBF file by name."
    )
    parser.add_argument("osm_file", help="Path to the .osm.pbf file")
    parser.add_argument("--output_dir", default=".")
    args = parser.parse_args()

    n_empty_ways = count_empty_ways(args.osm_file)
    if n_empty_ways > 0:
        sys.stderr.write(f"{args.osm_file} has empty ways and is likely corrupt.\n")
        sys.stderr.write("No data will be written.\n")
        sys.exit(1)

    out = subprocess.check_output(
        [
            *"osmium fileinfo --extended --no-crc --json --no-progress".split(" "),
            args.osm_file,
        ]
    )
    fileinfo = json.loads(out.decode("utf8"))
    count = fileinfo["data"]["count"]

    by_type = {
        "num-nodes": count["nodes"],
        "num-ways": count["ways"],
        "num-relations": count["relations"],
    }

    write_stats(
        args.output_dir,
        "feature",
        {},
        by_type,
    )


if __name__ == "__main__":
    main()
