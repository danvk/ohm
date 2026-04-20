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
        assert len(poly) == 1, "(Multi)Polygons must not have holes."
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
            # Deduplicate consecutive identical nodes (can arise from shapely
            # needle rings where two vertices quantize to the same grid cell).
            deduped: list[int] = [ring_ids[0]] if ring_ids else []
            for nid in ring_ids[1:]:
                if nid != deduped[-1]:
                    deduped.append(nid)
            # Discard degenerate rings: fewer than 3 nodes, or a node appears
            # more than once (spike/self-intersecting ring, e.g. [A, B, A]).
            if len(deduped) >= 3 and len(set(deduped)) == len(deduped):
                feat_ring_ids.append(deduped)
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
    junction_indices = [i for i, nid in enumerate(ring) if nid in junctions]

    if not junction_indices:
        # No junctions – entire ring is one segment.  Rotate to the minimum
        # node ID so that two traversals of the same closed ring (starting at
        # different positions) produce the same canonical segment and are
        # deduplicated correctly (e.g. an island shared between two features).
        min_idx = ring.index(min(ring))
        rotated = ring[min_idx:] + ring[:min_idx]
        return [tuple(rotated) + (rotated[0],)]

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
# Step 5b – Remove spur ways
# ---------------------------------------------------------------------------


def remove_spur_ways(
    way_map: dict[SegKey, int],
    feature_way_refs: list[list[list[tuple[int, bool]]]],
) -> tuple[dict[SegKey, int], list[list[list[tuple[int, bool]]]]]:
    """Remove spur way segments — those with a dead-end (degree-1) endpoint.

    A spur arises when a polygon ring has a spike: the boundary goes out to a
    tip node and returns along the same path.  Because edges are stored as
    unordered pairs, both traversals collapse to one edge, leaving the tip
    with degree 1 in the edge graph.  The segment from the last junction to
    the tip is then a dangling way that has no topological role.

    Removal is iterated until no more spurs exist (pruning one spur can expose
    the next node in the chain as a new dead-end).

    Closed segments (first node == last node, i.e. a ring with no junctions)
    are never considered spurs.
    """
    n_removed = 0
    while True:
        # Count how many (open) ways use each endpoint node
        endpoint_count: dict[int, int] = defaultdict(int)
        for canon_seg in way_map:
            if canon_seg[0] == canon_seg[-1]:
                continue  # closed loop – not a spur candidate
            endpoint_count[canon_seg[0]] += 1
            endpoint_count[canon_seg[-1]] += 1

        spur_ids = {
            wid
            for canon_seg, wid in way_map.items()
            if canon_seg[0] != canon_seg[-1]
            and (
                endpoint_count[canon_seg[0]] == 1 or endpoint_count[canon_seg[-1]] == 1
            )
        }

        if not spur_ids:
            break

        n_removed += len(spur_ids)
        way_map = {seg: wid for seg, wid in way_map.items() if wid not in spur_ids}
        feature_way_refs = [
            [
                [(wid, rev) for wid, rev in ring if wid not in spur_ids]
                for ring in feat_rings
            ]
            for feat_rings in feature_way_refs
        ]

    if n_removed:
        print(f"  Removed {n_removed} spur way(s)", file=sys.stderr)

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
    tag_filter: tuple[str, set[str]] | None = None,
    chronology_relations: list[dict] | None = None,
) -> None:
    """Write nodes, ways and relations to an OSM PBF file.

    Optional ``chronology_relations`` is a list of dicts, each with:
      ``tags``               – tag dict for the chronology relation
      ``member_feat_indices`` – ordered list of indices into ``features``
                               whose relations will become members (role "")
    Chronology relations are written after all feature relations and reference
    them by their OSM relation IDs (``-(feat_idx + 1)``).
    """

    # Reverse lookups needed for filtering
    # canonical_seg -> way_id is way_map; we need way_id -> canonical_seg
    way_id_to_seg: dict[int, SegKey] = {v: k for k, v in way_map.items()}

    # Determine which features (relations) to export
    kept_feat_indices: list[int] = []
    for i, feat in enumerate(features):
        if tag_filter:
            key, allowed_values = tag_filter
            props = feat.get("properties") or {}
            val = str(props.get(key, ""))
            if val not in allowed_values:
                continue
        kept_feat_indices.append(i)

    # Collect used way IDs
    used_way_ids: set[int] = set()
    for i in kept_feat_indices:
        for ring in feature_way_refs[i]:
            for way_id, _ in ring:
                used_way_ids.add(way_id)

    # Collect used node IDs
    used_node_ids: set[int] = set()
    for wid in used_way_ids:
        seg = way_id_to_seg[wid]
        used_node_ids.update(seg)

    # Use positive IDs — osmium tools (IdFilter, etc.) require non-negative IDs.
    # Each type gets its own ID space; nodes, ways and relations occupy separate
    # namespaces in OSM so there is no collision.
    # node internal ID n  →  OSM node ID   n
    # way  internal ID w  →  OSM way  ID   w
    # relation index  r   →  OSM rel  ID   r+1
    # chronology rel  c   →  OSM rel  ID   len(features) + c + 1

    n_node, n_way, n_rel = 0, 0, 0

    with osmium.SimpleWriter(output_path, overwrite=True) as writer:
        # --- Nodes ---
        for qpt, nid in node_map.items():
            if nid not in used_node_ids:
                continue
            qlon, qlat = qpt
            lon, lat = _dequantize(qlon, qlat)
            writer.add_node(
                mutable.Node(
                    id=nid,
                    location=(lon, lat),
                    tags={},
                    version=1,
                    visible=True,
                )
            )
            n_node += 1

        # --- Ways ---
        for canon_seg, wid in way_map.items():
            if wid not in used_way_ids:
                continue
            node_refs = [nid for nid in canon_seg]
            writer.add_way(
                mutable.Way(
                    id=wid,
                    nodes=node_refs,
                    tags={"source": "ned"},
                    version=1,
                    visible=True,
                )
            )
            n_way += 1

        # --- Feature relations ---
        for feat_idx in kept_feat_indices:
            feat = features[feat_idx]
            props = feat.get("properties") or {}
            tags = {str(k): str(v) for k, v in props.items() if v is not None}

            members: list[tuple[str, int, str]] = []
            for ring_way_refs in feature_way_refs[feat_idx]:
                for way_id, is_reversed in ring_way_refs:
                    role = "outer"  # all rings are outer (holes ignored)
                    members.append(("w", way_id, role))

            writer.add_relation(
                mutable.Relation(
                    id=feat_idx + 1,
                    members=members,
                    tags=tags,
                    version=1,
                    visible=True,
                )
            )
            n_rel += 1

        # --- Chronology relations ---
        if chronology_relations:
            for chron_idx, chron in enumerate(chronology_relations):
                chron_id = len(features) + chron_idx + 1
                members = [("r", fi + 1, "") for fi in chron["member_feat_indices"]]
                writer.add_relation(
                    mutable.Relation(
                        id=chron_id,
                        members=members,
                        tags={str(k): str(v) for k, v in chron["tags"].items()},
                        version=1,
                        visible=True,
                    )
                )
                n_rel += 1

    # Summary
    print(
        f"\nSummary: {n_node} nodes, {n_way} ways, {n_rel} relations",
        file=sys.stderr,
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
    parser.add_argument(
        "--filter",
        metavar="KEY=VAL1,VAL2,...",
        help="Only output relations matching tag KEY with value in {VAL1, VAL2, ...} (and their constituent ways/nodes)",
    )
    args = parser.parse_args()

    GRID = args.grid

    tag_filter: tuple[str, set[str]] | None = None
    if args.filter:
        if "=" not in args.filter:
            parser.error("Filter argument must be in the format KEY=VAL1,VAL2,...")
        key, vals = args.filter.split("=", 1)
        tag_filter = (key, set(vals.split(",")))

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
    write_osm(args.output, features, node_map, way_map, feature_way_refs, tag_filter)
    print("Done.", file=sys.stderr)


if __name__ == "__main__":
    main()
