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

Each file is a JSON object mapping string IDs to their data.
"""

import argparse
import json
import sys
import time
from typing import Any

import osmium

from geometry import build_polygon_rings


def tags_to_dict(tags) -> dict[str, str]:
    return {
        tag.k: tag.v
        for tag in tags
        # Multilingual names take a lot of storage space
        if tag.k in ("name", "name:en") or not tag.k.startswith("name")
    }


def _log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


def quantize(pt: tuple[float, float]) -> tuple[int, int]:
    lng, lat = pt
    return (round((lng + 180) / 360 * 4_000_000), round((lat + 90) / 180 * 2_000_000))


# ADMIN_LEVELS = {"2", "3", "4"}
ADMIN_LEVELS = {"2"}


class RelationHandler(osmium.SimpleHandler):
    """Collect admin boundary relations (admin_level 2/3/4) and their way members."""

    def __init__(self, tag_filter: tuple[str, set[str]] | None = None) -> None:
        super().__init__()
        # relation_id (int) → {"tags": {...}, "ways": [way_id, ...]}
        self.relations: dict[int, dict[str, Any]] = {}
        # set of way IDs referenced by collected relations
        self.way_ids: set[int] = set()
        self._tag_filter = tag_filter

    def relation(self, r: Any) -> None:
        tags = r.tags
        if tags.get("boundary") != "administrative":
            return
        if tags.get("admin_level") not in ADMIN_LEVELS:
            return
        if self._tag_filter is not None:
            key, allowed_values = self._tag_filter
            if tags.get(key) not in allowed_values:
                return

        outer_ways = [
            m.ref for m in r.members if m.type == "w" and m.role in ("outer", "")
        ]
        inner_ways = [m.ref for m in r.members if m.type == "w" and m.role == "inner"]
        all_ways = outer_ways + inner_ways
        self.relations[r.id] = {
            "tags": tags_to_dict(tags),
            "outer_ways": outer_ways,
            "inner_ways": inner_ways,
        }
        self.way_ids.update(all_ways)


class WayHandler(osmium.SimpleHandler):
    """Collect ways that appear in admin boundary relations."""

    def __init__(self, way_ids: set[int]) -> None:
        super().__init__()
        self._way_ids = way_ids
        # way_id (int) → quantized delta-encoded flat list (for output)
        self.ways: dict[int, list[int]] = {}
        # way_id (int) → ordered list of node IDs (for ring topology)
        self.way_nodes: dict[int, list[int]] = {}
        # way_id (int) → ordered list of (lon, lat) float tuples (for orientation)
        self.way_coords: dict[int, list[tuple[float, float]]] = {}

    def way(self, w: Any) -> None:
        if w.id not in self._way_ids:
            return
        valid_nodes = [(n.ref, (n.lon, n.lat)) for n in w.nodes if n.location.valid()]
        if not valid_nodes:
            return
        node_ids = [ref for ref, _ in valid_nodes]
        coords = [lonlat for _, lonlat in valid_nodes]
        self.way_nodes[w.id] = node_ids
        self.way_coords[w.id] = coords
        locs = [quantize(c) for c in coords]
        deltas = [
            locs[0],
            *[(nx - px, ny - py) for (px, py), (nx, ny) in zip(locs, locs[1:])],
        ]
        self.ways[w.id] = [coord for delta in deltas for coord in delta]


def parse_date_key(date_str: str) -> tuple:
    """Parse a date string into a sortable tuple.

    Handles formats: YYYY, YYYY-MM, YYYY-MM-DD, and negative years.
    Returns a tuple that sorts correctly.
    """
    # Handle leading negative sign for negative years
    is_negative = date_str.startswith("-")
    if is_negative:
        date_str = date_str[1:]

    parts = date_str.split("-")
    try:
        year = int(parts[0])
        if is_negative:
            year = -year
        month = int(parts[1]) if len(parts) > 1 else 0
        day = int(parts[2]) if len(parts) > 2 else 0
        return (year, month, day)
    except (ValueError, IndexError):
        return (9999, 12, 31)  # Invalid dates sort last


def write_json(path: str, data: Any) -> None:
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
    parser.add_argument(
        "--filter",
        metavar="KEY=VAL1,VAL2,...",
        help="Only output relations matching tag KEY with value in {VAL1, VAL2, ...}",
    )
    args = parser.parse_args()

    tag_filter: tuple[str, set[str]] | None = None
    if args.filter:
        if "=" not in args.filter:
            parser.error("--filter must be in the format KEY=VAL1,VAL2,...")
        key, vals = args.filter.split("=", 1)
        tag_filter = (key, set(vals.split(",")))

    osm_file = args.osm_file

    # --- Pass 1: Relations ---
    _log("Pass 1: scanning relations …")
    t0 = time.monotonic()
    rel_handler = RelationHandler(tag_filter=tag_filter)
    rel_handler.apply_file(osm_file, filters=[osmium.filter.KeyFilter("name")])
    elapsed = time.monotonic() - t0
    _log(
        f"  Found {len(rel_handler.relations):,} relations, "
        f"{len(rel_handler.way_ids):,} unique ways  ({elapsed:.1f}s)"
    )

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

    # --- Order ways in each relation into oriented rings, then write relations ---
    _log("Ordering ways into oriented rings …")
    for rid, rel_data in rel_handler.relations.items():
        outer_way_ids: list[int] = rel_data.pop("outer_ways")
        inner_way_ids: list[int] = rel_data.pop("inner_ways")
        polygons = build_polygon_rings(
            outer_way_ids,
            inner_way_ids,
            way_handler.way_nodes,
            way_handler.way_coords,
            warn=lambda msg: _log(f"    Warning: {msg}"),
        )
        rel_data["ways"] = polygons

    relations_out = [{"id": rid, **data} for rid, data in rel_handler.relations.items()]
    relations_out.sort(key=lambda r: parse_date_key(r["tags"].get("end_date", "2030")))
    write_json(args.relations_out, relations_out)

    _log("Done.")


if __name__ == "__main__":
    main()
