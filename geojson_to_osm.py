"""Convert a GeoJSON file of Polygons/MultiPolygons to an OSM PBF file.

Performs topological extraction so that shared boundaries between adjacent
polygons are represented as shared OSM ways rather than duplicated geometry.

Algorithm:
  1. Round coordinates to a grid (~1-10 m precision) and assign each unique
     point a node ID.
  2. Enumerate all rings (outer only; holes are ignored).  Build per-feature
     ring lists.
  3. Find "junction" nodes – nodes where the graph of edges (unordered pairs
     of adjacent node IDs) has degree ≠ 2.  Degree-2 nodes lie in the
     interior of a chain and are never split points.  Degree-1 nodes are
     dead-ends (rare in valid polygons); degree ≥ 3 nodes are true
     topological junctions (T/X intersections).  Because shared boundaries
     are traversed in *opposite* directions by adjacent polygons, we treat
     each edge as an unordered pair so that both traversal directions
     contribute the same edge.
  4. Split every ring at junction nodes to produce maximal "way segments".
  5. Deduplicate way segments: a segment that is the reverse of another is
     the same way (since we are working with closed polygons).  Assign way IDs.
  6. Write nodes → ways → relations to an OSM PBF via osmium.SimpleWriter.
     Every input GeoJSON feature becomes a relation with type=multipolygon.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict

import osmium
import osmium.osm.mutable as mutable

# ---------------------------------------------------------------------------
# Grid precision
# ---------------------------------------------------------------------------
# 1e-5 degrees ≈ 1.1 m – good enough to collapse "same" points
GRID = 1e-5


def _quantize(lon: float, lat: float) -> tuple[int, int]:
    """Round a coordinate to the nearest grid cell, returning integer keys."""
    return (round(lon / GRID), round(lat / GRID))


def _dequantize(qlon: int, qlat: int) -> tuple[float, float]:
    """Convert grid-cell keys back to float coordinates."""
    return (qlon * GRID, qlat * GRID)


# ---------------------------------------------------------------------------
# Step 1 – Collect rings from GeoJSON
# ---------------------------------------------------------------------------


def extract_rings(geom: dict) -> list[list[tuple[float, float]]]:
    """Return a list of outer rings (coordinate lists) from a geometry.

    Holes are ignored.  Coordinates are (lon, lat) float pairs.
    The closing duplicate point is stripped so every ring is an open sequence.
    """
    gtype = geom["type"]
    if gtype == "Polygon":
        polys = [geom["coordinates"]]
    elif gtype == "MultiPolygon":
        polys = geom["coordinates"]
    else:
        return []

    rings: list[list[tuple[float, float]]] = []
    for poly in polys:
        outer = poly[0]  # ignore holes
        # strip closing point if present
        pts = [(lon, lat) for lon, lat in outer]
        if len(pts) > 1 and pts[0] == pts[-1]:
            pts = pts[:-1]
        if len(pts) >= 3:
            rings.append(pts)
    return rings


# ---------------------------------------------------------------------------
# Step 2 – Build node index
# ---------------------------------------------------------------------------


def build_node_index(
    features: list[dict],
) -> tuple[
    dict[tuple[int, int], int],  # qpt -> node_id
    list[list[list[int]]],  # per-feature list of rings as node-id sequences
]:
    """Assign node IDs to all unique quantized points.

    Returns:
      node_map: mapping from quantized (qlon, qlat) to 1-based node ID
      feature_rings: for each feature, a list of rings; each ring is a list
                     of node IDs (not closed – the last ≠ first).
    """
    node_map: dict[tuple[int, int], int] = {}
    feature_rings: list[list[list[int]]] = []

    for feat in features:
        rings = extract_rings(feat["geometry"])
        feat_ring_ids: list[list[int]] = []
        for ring in rings:
            ring_ids: list[int] = []
            for lon, lat in ring:
                qpt = _quantize(lon, lat)
                if qpt not in node_map:
                    node_map[qpt] = len(node_map) + 1  # 1-based
                ring_ids.append(node_map[qpt])
            feat_ring_ids.append(ring_ids)
        feature_rings.append(feat_ring_ids)

    return node_map, feature_rings


# ---------------------------------------------------------------------------
# Step 3 – Find junction nodes
# ---------------------------------------------------------------------------


def find_junctions(feature_rings: list[list[list[int]]]) -> set[int]:
    """Determine which nodes are topological junctions.

    We model the polygon boundaries as an undirected multigraph: each
    consecutive pair of nodes in a ring contributes an undirected edge
    (frozenset of the two node IDs).  Because adjacent polygons traverse a
    shared boundary in *opposite* directions, both traversals produce the
    same unordered edge, so using frozensets correctly deduplicates them.

    A node is a junction iff its degree in this graph ≠ 2.
      - degree = 2  → interior node on a chain (not a split point)
      - degree = 1  → dead-end (should not occur in valid closed rings)
      - degree ≥ 3  → true topological junction (T- or X-intersection)
      - degree = 0  → isolated (shouldn't occur)

    Nodes at the start/end of shared segments naturally acquire degree ≥ 3
    (they are connected to the neighbours from both polygons on either side
    of the junction), so the split happens exactly at the right places.
    """
    # node_id -> set of incident unordered edges (each edge = frozenset of 2 node IDs)
    node_edges: dict[int, set[frozenset[int]]] = defaultdict(set)

    for feat_rings in feature_rings:
        for ring in feat_rings:
            n = len(ring)
            for i, nid in enumerate(ring):
                nb = ring[(i + 1) % n]
                edge: frozenset[int] = frozenset((nid, nb))
                node_edges[nid].add(edge)
                node_edges[nb].add(edge)

    junctions: set[int] = set()
    for nid, edges in node_edges.items():
        if len(edges) != 2:
            junctions.add(nid)

    return junctions


# ---------------------------------------------------------------------------
# Step 4 – Split rings into way segments at junctions
# ---------------------------------------------------------------------------


def split_ring_at_junctions(
    ring: list[int], junctions: set[int]
) -> list[tuple[int, ...]]:
    """Split a ring (open sequence of node IDs) into maximal segments.

    A segment starts and ends at a junction node.  If no junctions are
    present in the ring the whole ring becomes one segment (closed: first
    node is repeated at the end).

    Returns a list of tuples of node IDs.  Each tuple has its start and end
    in ``junctions`` (or the ring is entirely non-junction and the single
    segment is closed).
    """
    n = len(ring)
    junction_indices = [i for i, nid in enumerate(ring) if nid in junctions]

    if not junction_indices:
        # no junctions – entire ring is one segment; close it
        return [tuple(ring) + (ring[0],)]

    segments: list[tuple[int, ...]] = []
    num_j = len(junction_indices)

    for k in range(num_j):
        start_idx = junction_indices[k]
        end_idx = junction_indices[(k + 1) % num_j]

        if end_idx > start_idx:
            seg = ring[start_idx : end_idx + 1]
        else:
            # wrap around
            seg = ring[start_idx:] + ring[: end_idx + 1]

        segments.append(tuple(seg))

    return segments


# ---------------------------------------------------------------------------
# Step 5 – Deduplicate way segments
# ---------------------------------------------------------------------------

SegKey = tuple[int, ...]


def canonical_segment(seg: tuple[int, ...]) -> SegKey:
    """Return a canonical form of a segment for deduplication.

    A segment and its exact reverse represent the same boundary edge.
    We choose the lexicographically smaller of the two as the canonical form.
    """
    rev = tuple(reversed(seg))
    return min(seg, rev)


def build_ways(
    feature_rings: list[list[list[int]]],
    junctions: set[int],
) -> tuple[
    dict[SegKey, int],  # canonical_seg -> way_id
    list[list[list[tuple[int, bool]]]],  # per-feature, per-ring: [(way_id, reversed)]
]:
    """Split all rings into segments, deduplicate, assign way IDs.

    Returns:
      way_map: canonical segment -> 1-based way ID
      feature_way_refs: for each feature, for each ring, a list of
                        (way_id, is_reversed) tuples in ring order.
    """
    way_map: dict[SegKey, int] = {}
    feature_way_refs: list[list[list[tuple[int, bool]]]] = []

    for feat_rings in feature_rings:
        feat_way_refs: list[list[tuple[int, bool]]] = []
        for ring in feat_rings:
            ring_way_refs: list[tuple[int, bool]] = []
            segments = split_ring_at_junctions(ring, junctions)
            for seg in segments:
                canon = canonical_segment(seg)
                if canon not in way_map:
                    way_map[canon] = len(way_map) + 1  # 1-based
                way_id = way_map[canon]
                is_reversed = canon != seg
                ring_way_refs.append((way_id, is_reversed))
            feat_way_refs.append(ring_way_refs)
        feature_way_refs.append(feat_way_refs)

    return way_map, feature_way_refs


# ---------------------------------------------------------------------------
# Step 6 – Write OSM PBF
# ---------------------------------------------------------------------------


def write_osm(
    output_path: str,
    features: list[dict],
    node_map: dict[tuple[int, int], int],
    way_map: dict[SegKey, int],
    feature_way_refs: list[list[list[tuple[int, bool]]]],
) -> None:
    """Write nodes, ways and relations to an OSM PBF file."""

    # Reverse lookups
    id_to_qpt: dict[int, tuple[int, int]] = {v: k for k, v in node_map.items()}
    # canonical_seg -> way_id is way_map; we also need way_id -> canonical_seg
    way_id_to_seg: dict[int, SegKey] = {v: k for k, v in way_map.items()}

    # OSM IDs: nodes start at 1, ways after nodes, relations after ways
    # We'll use the 1-based IDs as-is (they don't overlap since we use
    # separate id spaces assigned during construction).
    # Node IDs:     1 … len(node_map)
    # Way IDs:      1 … len(way_map)   – these are written to a separate namespace
    # OSM doesn't have namespaces, so we offset ways and relations to avoid clashes.
    node_id_offset = 0
    way_id_offset = len(node_map)
    relation_id_offset = len(node_map) + len(way_map)

    with osmium.SimpleWriter(output_path, overwrite=True) as writer:
        # --- Nodes ---
        for qpt, nid in node_map.items():
            qlon, qlat = qpt
            lon, lat = _dequantize(qlon, qlat)
            writer.add_node(
                mutable.Node(
                    id=nid + node_id_offset,
                    location=(lon, lat),
                    tags={},
                    version=1,
                    visible=True,
                )
            )

        # --- Ways ---
        for canon_seg, wid in way_map.items():
            # node IDs in the canonical segment are 1-based; add offset
            node_refs = [nid + node_id_offset for nid in canon_seg]
            writer.add_way(
                mutable.Way(
                    id=wid + way_id_offset,
                    nodes=node_refs,
                    tags={},
                    version=1,
                    visible=True,
                )
            )

        # --- Relations ---
        for feat_idx, feat in enumerate(features):
            props = feat.get("properties") or {}
            tags = {str(k): str(v) for k, v in props.items() if v is not None}
            tags["type"] = "multipolygon"

            members: list[tuple[str, int, str]] = []
            for ring_way_refs in feature_way_refs[feat_idx]:
                for way_id, is_reversed in ring_way_refs:
                    osm_way_id = way_id + way_id_offset
                    role = "outer"  # all rings are outer (holes ignored)
                    members.append(("w", osm_way_id, role))

            rel_id = feat_idx + 1 + relation_id_offset
            writer.add_relation(
                mutable.Relation(
                    id=rel_id,
                    members=members,
                    tags=tags,
                    version=1,
                    visible=True,
                )
            )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    global GRID

    parser = argparse.ArgumentParser(
        description=(
            "Convert a GeoJSON file of Polygons/MultiPolygons to an OSM PBF, "
            "extracting shared topology (nodes and ways are deduplicated across features)."
        )
    )
    parser.add_argument("input", help="Input GeoJSON file")
    parser.add_argument("output", help="Output OSM PBF file (e.g. out.osm.pbf)")
    parser.add_argument(
        "--grid",
        type=float,
        default=GRID,
        metavar="DEGREES",
        help=f"Grid cell size in degrees for coordinate rounding (default: {GRID})",
    )
    args = parser.parse_args()

    GRID = args.grid

    print(f"Reading {args.input} …", file=sys.stderr)
    with open(args.input) as f:
        data = json.load(f)

    features: list[dict] = data["features"] if "features" in data else [data]
    print(f"  {len(features)} features", file=sys.stderr)

    # Step 1 – assign node IDs
    print("Building node index …", file=sys.stderr)
    node_map, feature_rings = build_node_index(features)
    print(f"  {len(node_map)} unique nodes", file=sys.stderr)

    # Step 2 – find junctions
    print("Finding junction nodes …", file=sys.stderr)
    junctions = find_junctions(feature_rings)
    print(f"  {len(junctions)} junction nodes", file=sys.stderr)

    # Step 3 – split into ways and deduplicate
    print("Building and deduplicating ways …", file=sys.stderr)
    way_map, feature_way_refs = build_ways(feature_rings, junctions)
    print(f"  {len(way_map)} unique ways", file=sys.stderr)

    # Step 4 – write output
    print(f"Writing {args.output} …", file=sys.stderr)
    write_osm(args.output, features, node_map, way_map, feature_way_refs)
    print("Done.", file=sys.stderr)

    # Summary
    n_nodes = len(node_map)
    n_ways = len(way_map)
    n_rels = len(features)
    print(
        f"\nSummary: {n_nodes} nodes, {n_ways} ways, {n_rels} relations",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
