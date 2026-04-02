import argparse
import json
import subprocess

from stats import write_stats


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Find elements in an OSM PBF file by name."
    )
    parser.add_argument("osm_file", help="Path to the .osm.pbf file")
    parser.add_argument("--output_dir", default=".")
    args = parser.parse_args()

    out = subprocess.check_output(
        [
            *"uv run osmium fileinfo --extended --no-crc --json --no-progress".split(
                " "
            ),
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
