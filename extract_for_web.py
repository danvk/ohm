"""Extract admin boundary relations, ways, and nodes for web visualization.

Performs three passes over a planet.osm.pbf file:

  Pass 0 - Chronologies: collect all relations with type=chronology.  These
            have other relations as ordered members.  Build a map from each
            member relation ID to the chronology metadata (id, name, prev, next)
            that will be embedded in the output.

  Pass 1 - Relations: collect all relations with boundary=administrative and
            admin_level in {2, 3, 4}.  Output their tags and the list of
            constituent way IDs.  Build the set of way IDs to fetch.

  Pass 2 - Ways: collect every way whose ID appears in the set built in pass 1.
            Output the ordered list of node IDs for each way.  Build the set of
            node IDs to fetch.

Output files (written to the current directory by default):
  relations.json
  ways.json

Each file is a JSON object mapping string IDs to their data.
"""

import argparse
import base64
import json
import struct
import sys
import time
from typing import Any

import osmium
import osmium.filter
import osmium.osm

from geometry import build_polygon_rings, rdp_simplify, vw_simplify
from graph_coloring import build_adjacency, dsatur_color, greedy_color
from stats import log_finish, log_start


def tags_to_dict(tags) -> dict[str, str]:
    return {
        tag.k: tag.v
        for tag in tags
        # Multilingual names take a lot of storage space
        if tag.k in ("name", "name:en") or not tag.k.startswith("name")
    }


def log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


def quantize(pt: tuple[float, float]) -> tuple[int, int]:
    lng, lat = pt
    return (round((lng + 180) / 360 * 4_000_000), round((lat + 90) / 180 * 2_000_000))


class ChronologyHandler(osmium.SimpleHandler):
    """Collect type=chronology relations and build a per-member lookup.

    For each member relation, stores a list of
    ``{"id": int, "name": str, "prev": int|None, "next": int|None}`` dicts —
    one entry per chronology the member belongs to.
    """

    def __init__(self) -> None:
        super().__init__()
        # member_relation_id → list of chronology entries
        self.by_member: dict[int, list[dict[str, Any]]] = {}
        self.chronology_count: int = 0

    def relation(self, r: Any) -> None:
        if r.tags.get("type") != "chronology":
            return
        self.chronology_count += 1
        chrono_id = r.id
        chrono_name = r.tags.get("name:en") or r.tags.get("name")
        # Members are stored in chronological order; all are relation members.
        members = [m.ref for m in r.members if m.type == "r"]
        for i, member_id in enumerate(members):
            prev_id = members[i - 1] if i > 0 else None
            next_id = members[i + 1] if i < len(members) - 1 else None
            entry: dict[str, Any] = {"id": chrono_id, "name": chrono_name}
            if prev_id is not None:
                entry["prev"] = prev_id
            if next_id is not None:
                entry["next"] = next_id
            self.by_member.setdefault(member_id, []).append(entry)


class RelationHandler(osmium.SimpleHandler):
    """Collect admin boundary relations (admin_level 2/3/4) and their way members."""

    def __init__(
        self, admin_levels: set[str], tag_filter: tuple[str, set[str]] | None = None
    ) -> None:
        super().__init__()
        # relation_id (int) → {"tags": {...}, "ways": [way_id, ...]}
        self.relations: dict[int, dict[str, Any]] = {}
        # set of way IDs referenced by collected relations
        self.way_ids: set[int] = set()
        # set of node IDs that are direct members of collected relations
        self.node_ids: set[int] = set()
        self.admin_levels = admin_levels
        self.tag_filter = tag_filter

    def relation(self, r: Any) -> None:
        tags = r.tags
        if tags.get("boundary") != "administrative":
            return
        if tags.get("admin_level") not in self.admin_levels:
            return
        if self.tag_filter is not None:
            key, allowed_values = self.tag_filter
            if tags.get(key) not in allowed_values:
                return

        outer_ways = [
            m.ref for m in r.members if m.type == "w" and m.role in ("outer", "")
        ]
        inner_ways = [m.ref for m in r.members if m.type == "w" and m.role == "inner"]
        all_ways = outer_ways + inner_ways
        node_members = [m.ref for m in r.members if m.type == "n"]
        rel_data: dict[str, Any] = {
            "tags": tags_to_dict(tags),
            "outer_ways": outer_ways,
            "inner_ways": inner_ways,
        }
        if node_members:
            rel_data["node_members"] = node_members
        self.relations[r.id] = rel_data
        self.way_ids.update(all_ways)
        self.node_ids.update(node_members)


class NodeHandler(osmium.SimpleHandler):
    """Collect nodes that are direct members of admin boundary relations."""

    def __init__(self, node_ids: set[int]) -> None:
        super().__init__()
        self._node_ids = node_ids
        # node_id (int) → {"loc": [lon, lat], "tags": {...}}
        self.nodes: dict[int, dict[str, Any]] = {}

    def node(self, n: Any) -> None:
        if n.id not in self._node_ids:
            return
        if not n.location.valid():
            return
        self.nodes[n.id] = {
            "loc": [n.location.lon, n.location.lat],
            "tags": tags_to_dict(n.tags),
        }


# Default simplification tolerance in meters (converted to quantized units at runtime).
# 1 quantized unit ≈ 10 m at the equator (360° / 4 000 000 ≈ 0.000090° ≈ 10 m).
_DEFAULT_SIMPLIFY_TOLERANCE_M = 10.0
# Default Visvalingam–Whyatt area threshold in m² (used for closed rings).
# 1 unit² ≈ 100 m²; 50 m² ≈ 0.5 unit² is comparable to RDP at 10 m.
_DEFAULT_VW_TOLERANCE_M2 = 50.0


def _kept_indices(original: list, simplified: list) -> list[int]:
    """Return the indices in *original* that correspond to the points in *simplified*.

    RDP returns a subsequence of the input list.  The first and last simplified
    points always correspond to original[0] and original[-1] by construction,
    so we anchor those directly and forward-scan only the interior points.

    A pure forward scan would fail when the last coordinate appears more than
    once in *original* (e.g. duplicate endpoint nodes), incorrectly mapping
    simplified[-1] to an earlier occurrence rather than original[-1].
    """
    if not simplified:
        return []
    if len(simplified) == 1:
        return [0]

    indices: list[int] = [0]  # simplified[0] always maps to original[0]
    j = 1
    search_end = len(original) - 1  # reserve original[-1] for simplified[-1]
    for i in range(1, search_end):
        if j < len(simplified) - 1 and original[i] == simplified[j]:
            indices.append(i)
            j += 1
    indices.append(len(original) - 1)  # simplified[-1] always maps to original[-1]
    return indices


class WayHandler(osmium.SimpleHandler):
    """Collect ways that appear in admin boundary relations."""

    def __init__(
        self,
        way_ids: set[int],
        rdp_tolerance: float = 1.0,
        vw_tolerance: float = 0.5,
    ) -> None:
        super().__init__()
        self._way_ids = way_ids
        self._rdp_tolerance = rdp_tolerance
        self._vw_tolerance = vw_tolerance
        # way_id (int) → quantized delta-encoded flat list (for output)
        self.ways: dict[int, list[int]] = {}
        # way_id (int) → ordered list of node IDs (for ring topology)
        self.way_nodes: dict[int, list[int]] = {}
        # way_id (int) → ordered list of (lon, lat) float tuples (for orientation)
        self.way_coords: dict[int, list[tuple[float, float]]] = {}
        # simplification stats
        self.nodes_before: int = 0
        self.nodes_after: int = 0

    def way(self, w: Any) -> None:
        if w.id not in self._way_ids:
            return
        valid_nodes = [(n.ref, (n.lon, n.lat)) for n in w.nodes if n.location.valid()]
        if not valid_nodes:
            return
        node_ids = [ref for ref, _ in valid_nodes]
        coords = [lonlat for _, lonlat in valid_nodes]
        locs = [quantize(c) for c in coords]

        # Simplify interior nodes.
        # Closed ways (rings) use Visvalingam–Whyatt (area-based, handles rings
        # natively).  Open ways use Ramer-Douglas-Peucker.
        # We work in quantized space: 1 unit ≈ 10 m, 1 unit² ≈ 100 m².
        is_closed = len(locs) >= 2 and locs[0] == locs[-1]
        if is_closed:
            simplified = vw_simplify(locs, tolerance=self._vw_tolerance)
        else:
            simplified = rdp_simplify(locs, tolerance=self._rdp_tolerance)
        self.nodes_before += len(locs)
        self.nodes_after += len(simplified)

        # Use index-based comparison instead
        simplified_indices = _kept_indices(locs, simplified)
        simp_node_ids = [node_ids[i] for i in simplified_indices]
        simp_coords = [coords[i] for i in simplified_indices]

        self.way_nodes[w.id] = simp_node_ids
        self.way_coords[w.id] = simp_coords
        deltas = [
            simplified[0],
            *[
                (nx - px, ny - py)
                for (px, py), (nx, ny) in zip(simplified, simplified[1:])
            ],
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
    log(f"  Wrote {len(data):,} entries to {path}")


def process_admin_level(level: str, args, tag_filter, chrono_to_members, graph):
    osm_file = args.osm_file

    # --- Pass 1: Relations ---
    log(f"{level} Pass 1: scanning relations …")
    t0 = time.monotonic()
    rel_handler = RelationHandler({level}, tag_filter=tag_filter)
    rel_handler.apply_file(osm_file, filters=[osmium.filter.KeyFilter("name")])
    elapsed = time.monotonic() - t0
    log(
        f"  Found {len(rel_handler.relations):,} relations, "
        f"{len(rel_handler.way_ids):,} unique ways, "
        f"{len(rel_handler.node_ids):,} direct node members  ({elapsed:.1f}s)"
    )

    # Convert meters → quantized units (1 unit ≈ 10 m, 1 unit² ≈ 100 m²)
    rdp_tolerance = args.simplify_tolerance_m / 10.0
    vw_tolerance = args.vw_tolerance_m2 / 100.0

    # --- Pass 2: Ways ---
    log("Pass 2: scanning ways …")
    t0 = time.monotonic()
    way_handler = WayHandler(
        rel_handler.way_ids, rdp_tolerance=rdp_tolerance, vw_tolerance=vw_tolerance
    )
    way_handler.apply_file(
        osm_file, filters=[osmium.filter.IdFilter(rel_handler.way_ids)], locations=True
    )
    elapsed = time.monotonic() - t0
    removed = way_handler.nodes_before - way_handler.nodes_after
    pct = 100 * removed / way_handler.nodes_before if way_handler.nodes_before else 0
    log(
        f"  Found {len(way_handler.ways):,} ways in ({elapsed:.1f}s)  "
        f"nodes: {way_handler.nodes_before:,} → {way_handler.nodes_after:,} "
        f"({removed:,} removed, {pct:.1f}%)"
    )

    ways_out = {str(wid): data for wid, data in way_handler.ways.items()}
    write_json(f"{args.output_dir}/ways{level}.json", ways_out)

    # --- Pass 3: Nodes (direct relation members) ---
    nodes_out: dict[str, Any] = {}
    if rel_handler.node_ids:
        log("Pass 3: scanning nodes …")
        t0 = time.monotonic()
        node_handler = NodeHandler(rel_handler.node_ids)
        node_filter = osmium.filter.IdFilter(rel_handler.node_ids).enable_for(
            osmium.osm.NODE
        )
        node_handler.apply_file(osm_file, filters=[node_filter], locations=True)
        elapsed = time.monotonic() - t0
        log(f"  Found {len(node_handler.nodes):,} nodes  ({elapsed:.1f}s)")
        nodes_out = {str(nid): data for nid, data in node_handler.nodes.items()}
    else:
        log("Pass 3: no direct node members found, skipping.")
    write_json(f"{args.output_dir}/nodes{level}.json", nodes_out)

    # --- Order ways in each relation into oriented rings, then write relations ---
    log("Ordering ways into oriented rings …")
    for rid, rel_data in rel_handler.relations.items():
        outer_way_ids: list[int] = rel_data.pop("outer_ways")
        inner_way_ids: list[int] = rel_data.pop("inner_ways")
        polygons, poly_warnings = build_polygon_rings(
            outer_way_ids,
            inner_way_ids,
            way_handler.way_nodes,
            way_handler.way_coords,
            # We've already output the ways at this point, so it's inconvenient
            # to include any new, synthesized ways to close rings.
            leave_open_rings=True,
        )
        for msg in poly_warnings:
            log(f"    Warning: {msg}")
        rel_data["ways"] = [
            [
                base64.b64encode(struct.pack(f">{len(ring)}i", *ring)).decode()
                for ring in polygon
            ]
            for polygon in polygons
        ]

    # Attach node members to each relation that has them.
    for rid, rel_data in rel_handler.relations.items():
        node_members = rel_data.pop("node_members", None)
        if node_members:
            rel_data["nodes"] = node_members

    # Attach chronology membership to each relation that belongs to one.
    for rid, rel_data in rel_handler.relations.items():
        chrono_entries = chrono_to_members.get(rid)
        if chrono_entries:
            rel_data["chronology"] = chrono_entries

    # --- Optional: graph coloring; Inject color into relations that have one ---
    if graph:
        rel_color, canonical_id = graph
        for rid, rel_data in rel_handler.relations.items():
            if rid in rel_color:
                rel_data["tags"]["color"] = rel_color[rid]
                rel_data["tags"]["color:id"] = canonical_id[rid]

    relations_out = [{"id": rid, **data} for rid, data in rel_handler.relations.items()]
    relations_out.sort(key=lambda r: parse_date_key(r["tags"].get("end_date", "2030")))
    write_json(f"{args.output_dir}/relations{level}.json", relations_out)


def color_graph(args):
    """Load graph data and produce ID->color, ID->canonical ID mappings."""
    if not args.graph:
        return None

    log("Loading graph and computing coloring …")
    with open(args.graph, encoding="utf-8") as f:
        graph = json.load(f)
    # Build adjacency and run coloring
    adj = build_adjacency(graph)
    if args.coloring == "dsatur":
        coloring = dsatur_color(adj)
    else:
        coloring = greedy_color(adj)
    log(f"  {len(set(coloring.values()))} colors used ({args.coloring})")

    # Map every member and dropped relation ID to its color
    rel_color: dict[int, int] = {}
    canonical_id: dict[int, int] = {}
    for nid_str, _node in graph["nodes"].items():
        color = coloring.get(int(nid_str))
        if color is None:
            continue
        for rid in _node.get("members", []) + _node.get("dropped", []):
            rel_color[rid] = color
            canonical_id[rid] = nid_str
        canonical_id[nid_str] = nid_str
    # Print per-color relation counts
    color_rel_counts: dict[int, int] = {}
    for c in rel_color.values():
        color_rel_counts[c] = color_rel_counts.get(c, 0) + 1
    for c in sorted(color_rel_counts):
        log(f"    color {c}: {color_rel_counts[c]:,} relations")

    return rel_color, canonical_id


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Extract admin boundary relations, ways, and nodes from an OSM PBF "
            "file for web visualization."
        )
    )
    parser.add_argument("osm_file", help="Path to the .osm.pbf file")
    parser.add_argument(
        "--output-dir",
        default="app/public",
        help="Output directory for JSON files",
    )
    parser.add_argument(
        "--filter",
        metavar="KEY=VAL1,VAL2,...",
        help="Only output relations matching tag KEY with value in {VAL1, VAL2, ...}",
    )
    parser.add_argument(
        "--simplify-tolerance-m",
        type=float,
        default=_DEFAULT_SIMPLIFY_TOLERANCE_M,
        metavar="METERS",
        help=(
            "Ramer-Douglas-Peucker simplification tolerance in meters for open ways "
            f"(default: {_DEFAULT_SIMPLIFY_TOLERANCE_M}). "
            "Set to 0 to disable simplification."
        ),
    )
    parser.add_argument(
        "--admin-levels",
        default="2",
        metavar="LEVELS",
        help=(
            "Comma-separated list of admin_level values to include "
            "(default: 2). Example: --admin-levels 2,3,4"
        ),
    )
    parser.add_argument(
        "--graph",
        metavar="GRAPH_JSON",
        default=None,
        help=(
            "Path to a graph.json produced by build_connectivity_graph.py.  "
            "When supplied, the script runs graph coloring and writes a "
            "'color' integer property on every relation that appears in the graph."
        ),
    )
    parser.add_argument(
        "--coloring",
        choices=["welsh-powell", "dsatur"],
        default="welsh-powell",
        help="Graph coloring algorithm to use (default: welsh-powell)",
    )
    parser.add_argument(
        "--vw-tolerance-m2",
        type=float,
        default=_DEFAULT_VW_TOLERANCE_M2,
        metavar="M2",
        help=(
            "Visvalingam–Whyatt area threshold in m² for closed rings "
            f"(default: {_DEFAULT_VW_TOLERANCE_M2}). "
            "Set to 0 to disable simplification for closed rings."
        ),
    )
    args = parser.parse_args()
    log_start(__file__)

    tag_filter: tuple[str, set[str]] | None = None
    if args.filter:
        if "=" not in args.filter:
            parser.error("--filter must be in the format KEY=VAL1,VAL2,...")
        key, vals = args.filter.split("=", 1)
        tag_filter = (key, set(vals.split(",")))

    # --- Pass 0: Chronologies ---
    log("Pass 0: scanning chronology relations …")
    t0 = time.monotonic()
    chrono_handler = ChronologyHandler()
    chrono_handler.apply_file(
        args.osm_file, filters=[osmium.filter.TagFilter(("type", "chronology"))]
    )
    elapsed = time.monotonic() - t0
    log(
        f"  Found {chrono_handler.chronology_count:,} chronologies covering "
        f"{len(chrono_handler.by_member):,} unique member relations  ({elapsed:.1f}s)"
    )

    graph = color_graph(args)

    admin_levels = args.admin_levels.split(",")
    for admin_level in admin_levels:
        log_start(f"admin_level={admin_level}")
        process_admin_level(
            admin_level, args, tag_filter, chrono_handler.by_member, graph
        )
        log_finish(f"admin_level={admin_level}")

    log("Done.")


if __name__ == "__main__":
    main()
