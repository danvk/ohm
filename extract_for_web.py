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

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def tags_to_dict(tags) -> dict[str, str]:
    return {tag.k: tag.v for tag in tags}


def _log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


# ---------------------------------------------------------------------------
# Pass 1 – Relations
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Pass 2 – Ways
# ---------------------------------------------------------------------------


class WayHandler(osmium.SimpleHandler):
    """Collect ways that appear in admin boundary relations."""

    def __init__(self, way_ids: set[int]) -> None:
        super().__init__()
        self._way_ids = way_ids
        # way_id (int) → {"nodes": [node_id, ...]}
        self.ways: dict[int, dict[str, Any]] = {}
        # set of node IDs referenced by collected ways
        self.node_ids: set[int] = set()

    def way(self, w: Any) -> None:
        if w.id not in self._way_ids:
            return
        node_refs = [n.ref for n in w.nodes]
        self.ways[w.id] = {"nodes": node_refs}
        self.node_ids.update(node_refs)


# ---------------------------------------------------------------------------
# Pass 3 – Nodes
# ---------------------------------------------------------------------------


class NodeHandler(osmium.SimpleHandler):
    """Collect nodes that appear in admin boundary ways."""

    def __init__(self, node_ids: set[int]) -> None:
        super().__init__()
        self._node_ids = node_ids
        # node_id (int) → {"lon": float, "lat": float}
        self.nodes: dict[int, dict[str, float]] = {}

    def node(self, n: Any) -> None:
        if n.id not in self._node_ids:
            return
        loc = n.location
        if not loc.valid():
            return
        self.nodes[n.id] = {"lon": loc.lon, "lat": loc.lat}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def write_json(path: str, data: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
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
    parser.add_argument(
        "--nodes-out",
        default="nodes.json",
        help="Output path for nodes JSON (default: nodes.json)",
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
        osm_file, filters=[osmium.filter.IdFilter(rel_handler.way_ids)]
    )
    elapsed = time.monotonic() - t0
    _log(
        f"  Found {len(way_handler.ways):,} ways, "
        f"{len(way_handler.node_ids):,} unique nodes  ({elapsed:.1f}s)"
    )

    ways_out = {str(wid): data for wid, data in way_handler.ways.items()}
    write_json(args.ways_out, ways_out)

    # --- Pass 3: Nodes ---
    _log("Pass 3: scanning nodes …")
    t0 = time.monotonic()
    node_handler = NodeHandler(way_handler.node_ids)
    node_handler.apply_file(
        osm_file, filters=[osmium.filter.IdFilter(way_handler.node_ids)]
    )
    elapsed = time.monotonic() - t0
    _log(f"  Found {len(node_handler.nodes):,} nodes  ({elapsed:.1f}s)")

    nodes_out = {str(nid): data for nid, data in node_handler.nodes.items()}
    write_json(args.nodes_out, nodes_out)

    _log("Done.")


if __name__ == "__main__":
    main()
