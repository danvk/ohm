import argparse
import json
import random
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


def count_orphaned_features(osm_file: str) -> tuple[int, int]:
    """Count untagged nodes not in any way, and untagged ways not in any relation."""
    # Pass 1: collect way IDs used by relations
    node_ids_in_ways: set[int] = set()
    way_ids_in_relations: set[int] = set()
    fp = osmium.FileProcessor(osm_file, osmium.osm.RELATION)
    for obj in fp:
        if isinstance(obj, osmium.osm.Relation):
            for member in obj.members:
                if member.type == "w":
                    way_ids_in_relations.add(member.ref)

    # Pass 2: count untagged ways not in any relation
    n_untagged_orphan_ways = 0
    untagged_orphan_ways: list[int] = []
    fp = osmium.FileProcessor(osm_file, osmium.osm.WAY)
    for obj in fp:
        if not isinstance(obj, osmium.osm.Way):
            continue
        if len(obj.tags) == 0 and obj.id not in way_ids_in_relations:
            n_untagged_orphan_ways += 1
            untagged_orphan_ways.append(obj.id)
        else:
            for node_ref in obj.nodes:
                node_ids_in_ways.add(node_ref.ref)

    # Pass 3: count untagged nodes not in any non-orphan way
    n_untagged_orphan_nodes = 0
    untagged_orphan_nodes: list[int] = []
    fp = osmium.FileProcessor(osm_file, osmium.osm.NODE)
    for obj in fp:
        if not isinstance(obj, osmium.osm.Node):
            continue
        if len(obj.tags) == 0 and obj.id not in node_ids_in_ways:
            n_untagged_orphan_nodes += 1
            untagged_orphan_nodes.append(obj.id)

    sys.stderr.write(
        f"{osm_file}: {n_untagged_orphan_nodes=} {n_untagged_orphan_ways=}\n"
    )
    print(
        "nodes: ", ", ".join(str(x) for x in random.sample(untagged_orphan_nodes, 100))
    )
    print("ways: ", ", ".join(str(x) for x in random.sample(untagged_orphan_ways, 100)))

    with open("orphan.ways.txt", "w") as out:
        out.writelines(f"{x}\n" for x in untagged_orphan_ways)
    with open("orphan.nodes.txt", "w") as out:
        out.writelines(f"{x}\n" for x in untagged_orphan_nodes)

    return n_untagged_orphan_nodes, n_untagged_orphan_ways


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

    n_untagged_orphan_nodes, n_untagged_orphan_ways = count_orphaned_features(
        args.osm_file
    )

    by_type = {
        "num-nodes": count["nodes"],
        "num-ways": count["ways"],
        "num-relations": count["relations"],
        "num-untagged-orphan-nodes": n_untagged_orphan_nodes,
        "num-untagged-orphan-ways": n_untagged_orphan_ways,
    }

    write_stats(
        args.output_dir,
        "feature",
        {},
        by_type,
    )


if __name__ == "__main__":
    main()
