"""Extract admin boundary relations, ways, and nodes for web visualization.

Performs three passes over a planet.osm.pbf file:

  Pass 1 - Relations: collect all relations with boundary=administrative and
            admin_level in {2, 3, 4}.  Output their tags and the list of
            constituent way IDs.  Build the set of way IDs to fetch.

  Pass 2 - Ways: collect every way whose ID appears in the set built in pass 1.
            Output the ordered list of node IDs for each way.  Build the set of
            node IDs to fetch.

  Pass 3 - Nodes: collect every node whose ID appears in the set built in pass 2.
            Output lon/lat for each node.

Output files (written to the current directory by default):
  relations.json
  ways.json
  nodes.json

Each file is a JSON object mapping string IDs to their data.
"""

import argparse
import json
import sys
import time
from typing import Any

import osmium


def tags_to_dict(tags) -> dict[str, str]:
    return {tag.k: tag.v for tag in tags}


def _log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


def quantize(pt: tuple[float, float]) -> tuple[int, int]:
    lng, lat = pt
    return (round((lng + 180) / 360 * 4_000_000), round((lat + 90) / 180 * 2_000_000))


ADMIN_LEVELS = {"2", "3", "4"}


class RelationHandler(osmium.SimpleHandler):
    """Collect admin boundary relations (admin_level 2/3/4) and their way members."""

    def __init__(self) -> None:
        super().__init__()
        # relation_id (int) → {"tags": {...}, "ways": [way_id, ...]}
        self.relations: dict[int, dict[str, Any]] = {}
        # set of way IDs referenced by collected relations
        self.way_ids: set[int] = set()

    def relation(self, r: Any) -> None:
        tags = r.tags
        if tags.get("boundary") != "administrative":
            return
        if tags.get("admin_level") not in ADMIN_LEVELS:
            return

        way_members = [m.ref for m in r.members if m.type == "w"]
        self.relations[r.id] = {
            "tags": tags_to_dict(tags),
            "ways": way_members,
        }
        self.way_ids.update(way_members)


class WayHandler(osmium.SimpleHandler):
    """Collect ways that appear in admin boundary relations."""

    def __init__(self, way_ids: set[int]) -> None:
        super().__init__()
        self._way_ids = way_ids
        # way_id (int) → {"nodes": [node_id, ...]}
        self.ways: dict[int, list[tuple[int, int]]] = {}

    def way(self, w: Any) -> None:
        if w.id not in self._way_ids:
            return
        locs = [quantize((n.lon, n.lat)) for n in w.nodes if n.location.valid()]
        if not locs:
            self.ways[w.id] = locs
        else:
            self.ways[w.id] = [
                locs[0],
                *[(nx - px, ny - py) for (px, py), (nx, ny) in zip(locs, locs[1:])],
            ]


def write_json(path: str, data: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
    _log(f"  Wrote {len(data):,} entries to {path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Extract admin boundary relations, ways, and nodes from an OSM PBF "
            "file for web visualization."
        )
    )
    parser.add_argument("osm_file", help="Path to the .osm.pbf file")
    parser.add_argument(
        "--relations-out",
        default="relations.json",
        help="Output path for relations JSON (default: relations.json)",
    )
    parser.add_argument(
        "--ways-out",
        default="ways.json",
        help="Output path for ways JSON (default: ways.json)",
    )
    args = parser.parse_args()

    osm_file = args.osm_file

    # --- Pass 1: Relations ---
    _log("Pass 1: scanning relations …")
    t0 = time.monotonic()
    rel_handler = RelationHandler()
    rel_handler.apply_file(osm_file, filters=[osmium.filter.KeyFilter("name")])
    elapsed = time.monotonic() - t0
    _log(
        f"  Found {len(rel_handler.relations):,} relations, "
        f"{len(rel_handler.way_ids):,} unique ways  ({elapsed:.1f}s)"
    )

    # Serialise relation IDs as strings for JSON keys
    relations_out = {str(rid): data for rid, data in rel_handler.relations.items()}
    write_json(args.relations_out, relations_out)

    # --- Pass 2: Ways ---
    _log("Pass 2: scanning ways …")
    t0 = time.monotonic()
    way_handler = WayHandler(rel_handler.way_ids)
    way_handler.apply_file(
        osm_file, filters=[osmium.filter.IdFilter(rel_handler.way_ids)], locations=True
    )
    elapsed = time.monotonic() - t0
    _log(f"  Found {len(way_handler.ways):,} ways in ({elapsed:.1f}s)")

    ways_out = {str(wid): data for wid, data in way_handler.ways.items()}
    write_json(args.ways_out, ways_out)

    _log("Done.")


if __name__ == "__main__":
    main()
