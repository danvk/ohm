"""Build a connectivity graph of admin_level=2 relations for map coloring.

Performs four passes over a planet.osm.pbf file:

  Pass 0 - Chronologies: collect all type=chronology relations and build a
            per-member lookup (member relation ID → chronology ID and members).

  Pass 1 - Relations: collect all relations with boundary=administrative and
            admin_level=2.  Record their tags (start_date, end_date) and
            the set of constituent way IDs.

  Pass 2 - Ways: for each way in the collected set, record which relations use
            it and fetch coordinates (needed for containment geometry checks).

  Post-processing:
    1. Deduplicate exact duplicates (same member ways, start_date, end_date).
       When one duplicate belongs to a chronology, keep that one.
    2. Group relations that share a chronology into a single graph node.
    3. Drop relations that are ≥90% geometrically contained within a
       co-temporal, border-sharing sibling (the larger absorbs the smaller).
    4. Build the edge list: two nodes share an edge if they share a member
       way AND have at least one pair of members whose date ranges overlap.
       This prevents spurious edges from OSM ways that are reused across
       very different historical eras (e.g. a modern border segment used
       to approximate both an ancient empire and a 20th-century state).

Output (written to --output, default: graph.json):
  {
    "nodes": {
      "<canonical_id>": {"members": [<rel_id>, ...]}
    },
    "edges": [[<id_a>, <id_b>], ...]
  }
"""

import argparse
import json
import sys
import time
from collections import defaultdict
from typing import Any

import osmium
import osmium.filter
import osmium.osm
from shapely.geometry import MultiPolygon, Polygon

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


def parse_date(date_str: str | None) -> tuple[int, int, int] | None:
    """Parse an OSM date string into a (year, month, day) tuple, or None."""
    if not date_str:
        return None
    is_neg = date_str.startswith("-")
    s = date_str[1:] if is_neg else date_str
    parts = s.split("-")
    try:
        year = int(parts[0])
        if is_neg:
            year = -year
        month = int(parts[1]) if len(parts) > 1 else 0
        day = int(parts[2]) if len(parts) > 2 else 0
        return (year, month, day)
    except (ValueError, IndexError):
        return None


def dates_overlap(
    start_a: tuple | None,
    end_a: tuple | None,
    start_b: tuple | None,
    end_b: tuple | None,
) -> bool:
    """Return True if [start_a, end_a) and [start_b, end_b) overlap.

    None for start means −∞; None for end means +∞.
    """
    _POS_INF = (9999, 12, 31)
    _NEG_INF = (-9999, 1, 1)
    sa = start_a if start_a is not None else _NEG_INF
    ea = end_a if end_a is not None else _POS_INF
    sb = start_b if start_b is not None else _NEG_INF
    eb = end_b if end_b is not None else _POS_INF
    # [sa, ea) ∩ [sb, eb) is non-empty iff sa < eb and sb < ea
    return sa < eb and sb < ea


# ---------------------------------------------------------------------------
# OSM Handlers
# ---------------------------------------------------------------------------


class ChronologyHandler(osmium.SimpleHandler):
    """Collect type=chronology relations."""

    def __init__(self) -> None:
        super().__init__()
        # chronology_id → ordered list of member relation IDs
        self.chronologies: dict[int, list[int]] = {}
        # member_relation_id → chronology_id
        self.member_to_chrono: dict[int, int] = {}

    def relation(self, r: Any) -> None:
        if r.tags.get("type") != "chronology":
            return
        members = [m.ref for m in r.members if m.type == "r"]
        self.chronologies[r.id] = members
        for mid in members:
            self.member_to_chrono[mid] = r.id


class RelationHandler(osmium.SimpleHandler):
    """Collect admin_level=2 relations."""

    def __init__(self) -> None:
        super().__init__()
        # relation_id → {tags, outer_ways, inner_ways}
        self.relations: dict[int, dict[str, Any]] = {}
        # set of all way IDs referenced
        self.way_ids: set[int] = set()

    def relation(self, r: Any) -> None:
        tags = r.tags
        if tags.get("boundary") != "administrative":
            return
        if tags.get("admin_level") != "2":
            return

        outer_ways = [
            m.ref for m in r.members if m.type == "w" and m.role in ("outer", "")
        ]
        inner_ways = [m.ref for m in r.members if m.type == "w" and m.role == "inner"]
        all_ways = outer_ways + inner_ways

        self.relations[r.id] = {
            "start_date": tags.get("start_date"),
            "end_date": tags.get("end_date"),
            "name": tags.get("name", ""),
            "outer_ways": outer_ways,
            "inner_ways": inner_ways,
            "all_ways": set(all_ways),
        }
        self.way_ids.update(all_ways)


class WayHandler(osmium.SimpleHandler):
    """Collect coordinates for all ways used by admin_level=2 relations."""

    def __init__(self, way_ids: set[int]) -> None:
        super().__init__()
        self._way_ids = way_ids
        # way_id → list of (lon, lat) float tuples
        self.way_coords: dict[int, list[tuple[float, float]]] = {}

    def way(self, w: Any) -> None:
        if w.id not in self._way_ids:
            return
        coords = [(n.lon, n.lat) for n in w.nodes if n.location.valid()]
        if len(coords) >= 2:
            self.way_coords[w.id] = coords


# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------


def _build_shapely_polygon(
    outer_ways: list[int],
    inner_ways: list[int],
    way_coords: dict[int, list[tuple[float, float]]],
) -> MultiPolygon | Polygon | None:
    """Build a Shapely geometry from outer/inner way lists.

    Ways are concatenated naively (order within each group is unspecified at
    this stage — we just need an approximate area for containment testing).
    Returns None if not enough coordinate data is available.
    """

    def _chain_ways(way_ids: list[int]) -> list[tuple[float, float]]:
        coords: list[tuple[float, float]] = []
        for wid in way_ids:
            wc = way_coords.get(wid)
            if wc:
                # Skip the first coord if it duplicates the last already added
                if coords and coords[-1] == wc[0]:
                    coords.extend(wc[1:])
                else:
                    coords.extend(wc)
        return coords

    outer_coords = _chain_ways(outer_ways)
    if len(outer_coords) < 3:
        return None

    try:
        outer_poly = Polygon(outer_coords)
        if not outer_poly.is_valid:
            outer_poly = outer_poly.buffer(0)
        if inner_ways:
            inner_coords = _chain_ways(inner_ways)
            if len(inner_coords) >= 3:
                inner_poly = Polygon(inner_coords)
                if not inner_poly.is_valid:
                    inner_poly = inner_poly.buffer(0)
                outer_poly = outer_poly.difference(inner_poly)
        return outer_poly
    except Exception:
        return None


def _containment_fraction(smaller_geom, larger_geom) -> float:
    """Return the fraction of *smaller_geom*'s area that lies inside *larger_geom*."""
    if smaller_geom is None or larger_geom is None:
        return 0.0
    try:
        smaller_area = smaller_geom.area
        if smaller_area == 0:
            return 0.0
        intersection = smaller_geom.intersection(larger_geom)
        return intersection.area / smaller_area
    except Exception:
        return 0.0


# ---------------------------------------------------------------------------
# Main logic
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build an admin_level=2 connectivity graph for map coloring."
    )
    parser.add_argument("osm_file", help="Path to the .osm.pbf file")
    parser.add_argument(
        "--output",
        default="graph.json",
        help="Output JSON file (default: graph.json)",
    )
    parser.add_argument(
        "--containment-threshold",
        type=float,
        default=0.90,
        metavar="FRAC",
        help=(
            "Fraction of smaller relation area that must lie inside the larger "
            "to be dropped (default: 0.90)"
        ),
    )
    args = parser.parse_args()

    osm_file = args.osm_file
    containment_threshold = args.containment_threshold

    # ------------------------------------------------------------------
    # Pass 0: Chronologies
    # ------------------------------------------------------------------
    _log("Pass 0: scanning chronology relations …")
    t0 = time.monotonic()
    chrono_handler = ChronologyHandler()
    chrono_handler.apply_file(
        osm_file, filters=[osmium.filter.TagFilter(("type", "chronology"))]
    )
    _log(
        f"  Found {len(chrono_handler.chronologies):,} chronologies covering "
        f"{len(chrono_handler.member_to_chrono):,} member relations  "
        f"({time.monotonic() - t0:.1f}s)"
    )

    # ------------------------------------------------------------------
    # Pass 1: Relations
    # ------------------------------------------------------------------
    _log("Pass 1: scanning admin_level=2 relations …")
    t0 = time.monotonic()
    rel_handler = RelationHandler()
    rel_handler.apply_file(osm_file, filters=[osmium.filter.KeyFilter("boundary")])
    relations: dict[int, dict[str, Any]] = rel_handler.relations
    _log(
        f"  Found {len(relations):,} relations, "
        f"{len(rel_handler.way_ids):,} unique ways  ({time.monotonic() - t0:.1f}s)"
    )

    # ------------------------------------------------------------------
    # Pass 2: Ways (with locations for geometry)
    # ------------------------------------------------------------------
    _log("Pass 2: scanning ways …")
    t0 = time.monotonic()
    way_handler = WayHandler(rel_handler.way_ids)
    way_handler.apply_file(
        osm_file,
        filters=[osmium.filter.IdFilter(rel_handler.way_ids)],
        locations=True,
    )
    way_coords = way_handler.way_coords
    _log(
        f"  Fetched coordinates for {len(way_coords):,} ways  "
        f"({time.monotonic() - t0:.1f}s)"
    )

    # ------------------------------------------------------------------
    # Step 1: Deduplicate exact duplicates
    # (same member ways + same start_date + same end_date)
    # ------------------------------------------------------------------
    _log("Step 1: deduplicating exact duplicates …")

    # Group by (frozenset(all_ways), start_date, end_date)
    dup_key: dict[tuple, list[int]] = defaultdict(list)
    for rid, rdata in relations.items():
        key = (frozenset(rdata["all_ways"]), rdata["start_date"], rdata["end_date"])
        dup_key[key].append(rid)

    removed: set[int] = set()
    for key, rids in dup_key.items():
        if len(rids) <= 1:
            continue
        # Among duplicates, prefer any that belongs to a chronology
        in_chrono = [r for r in rids if r in chrono_handler.member_to_chrono]
        if in_chrono:
            # Keep the first one that's in a chronology; remove the rest
            keep = in_chrono[0]
            to_remove = [r for r in rids if r != keep]
        else:
            # No chronology membership — keep the lowest ID (arbitrary but stable)
            keep = min(rids)
            to_remove = [r for r in rids if r != keep]
        for r in to_remove:
            removed.add(r)
        _log(f"  Duplicate group {rids}: keeping {keep}, removing {to_remove}")

    for r in removed:
        del relations[r]

    _log(
        f"  Removed {len(removed):,} exact duplicates; "
        f"{len(relations):,} relations remain"
    )

    # ------------------------------------------------------------------
    # Step 2: Group by chronology → graph nodes
    # Each chronology becomes one node (canonical ID = chronology ID).
    # Relations not in any chronology are their own nodes
    # (canonical ID = relation ID).
    # ------------------------------------------------------------------
    _log("Step 2: grouping by chronology …")

    # node_id → list of relation IDs collapsed into it
    nodes: dict[int, list[int]] = {}
    # relation_id → node_id
    rel_to_node: dict[int, int] = {}

    # First: handle relations that are members of a known chronology
    processed_chronologies: set[int] = set()
    for rid in list(relations.keys()):
        chrono_id = chrono_handler.member_to_chrono.get(rid)
        if chrono_id is None:
            continue
        if chrono_id in processed_chronologies:
            continue
        processed_chronologies.add(chrono_id)
        # All members of this chronology that are still in our relation set
        members_in_set = [
            m for m in chrono_handler.chronologies[chrono_id] if m in relations
        ]
        if not members_in_set:
            continue
        nodes[chrono_id] = members_in_set
        for m in members_in_set:
            rel_to_node[m] = chrono_id

    # Second: relations not assigned to any chronology node
    for rid in relations:
        if rid not in rel_to_node:
            nodes[rid] = [rid]
            rel_to_node[rid] = rid

    _log(
        f"  {len(relations):,} relations → {len(nodes):,} nodes "
        f"({len(processed_chronologies):,} from chronologies)"
    )

    # ------------------------------------------------------------------
    # Step 3: Drop relations that are ≥90% contained within a co-temporal
    # border-sharing sibling.  We work at the individual-relation level
    # (before further node merging) since nodes span time ranges.
    # ------------------------------------------------------------------
    _log("Step 3: containment filtering …")

    # Build a way → list[relation_id] index for fast overlap lookup
    way_to_rels: dict[int, list[int]] = defaultdict(list)
    for rid, rdata in relations.items():
        for wid in rdata["all_ways"]:
            way_to_rels[wid].append(rid)

    # Pre-compute Shapely polygons for each relation (lazy, cached)
    _geom_cache: dict[int, Any] = {}

    def get_geom(rid: int):
        if rid not in _geom_cache:
            rdata = relations[rid]
            _geom_cache[rid] = _build_shapely_polygon(
                rdata["outer_ways"], rdata["inner_ways"], way_coords
            )
        return _geom_cache[rid]

    contained_removed: set[int] = set()
    # Maps absorbing node_id → list of dropped relation IDs
    dropped_into: dict[int, list[int]] = defaultdict(list)

    # Only compare pairs that share at least one way (potential border neighbours)
    checked_pairs: set[frozenset] = set()
    for wid, rids in way_to_rels.items():
        for i in range(len(rids)):
            for j in range(i + 1, len(rids)):
                ra, rb = rids[i], rids[j]
                if ra in contained_removed or rb in contained_removed:
                    continue
                pair = frozenset((ra, rb))
                if pair in checked_pairs:
                    continue
                checked_pairs.add(pair)

                da = relations[ra]
                db = relations[rb]

                # Must have overlapping date ranges
                if not dates_overlap(
                    parse_date(da["start_date"]),
                    parse_date(da["end_date"]),
                    parse_date(db["start_date"]),
                    parse_date(db["end_date"]),
                ):
                    continue

                geom_a = get_geom(ra)
                geom_b = get_geom(rb)
                if geom_a is None or geom_b is None:
                    continue

                area_a = geom_a.area
                area_b = geom_b.area

                if area_a == 0 or area_b == 0:
                    continue

                # Test whether the smaller is ≥90% inside the larger
                if area_a <= area_b:
                    smaller, larger, smaller_id, larger_id = (
                        geom_a,
                        geom_b,
                        ra,
                        rb,
                    )
                else:
                    smaller, larger, smaller_id, larger_id = (
                        geom_b,
                        geom_a,
                        rb,
                        ra,
                    )

                frac = _containment_fraction(smaller, larger)
                if frac >= containment_threshold:
                    _log(
                        f"  Dropping {smaller_id} (contained {frac:.1%} "
                        f"within {larger_id})"
                    )
                    contained_removed.add(smaller_id)
                    absorbing_node = rel_to_node[larger_id]
                    dropped_into[absorbing_node].append(smaller_id)

    for rid in contained_removed:
        del relations[rid]
        # Remove from the node it belonged to
        node_id = rel_to_node.pop(rid, None)
        if node_id is not None and node_id in nodes:
            nodes[node_id] = [m for m in nodes[node_id] if m != rid]
            if not nodes[node_id]:
                del nodes[node_id]

    _log(
        f"  Removed {len(contained_removed):,} contained relations; "
        f"{len(relations):,} remain, {len(nodes):,} nodes"
    )

    # ------------------------------------------------------------------
    # Step 4: Build the edge list from shared member ways
    # Two nodes share an edge if they share a member way AND have at least
    # one pair of member relations with overlapping [start_date, end_date)
    # ranges.  The temporal guard prevents spurious edges from OSM ways
    # that are reused across different historical eras.
    # ------------------------------------------------------------------
    _log("Step 4: building edges …")

    # Pre-compute date ranges for each relation (as parsed tuples)
    rel_dates: dict[int, tuple] = {
        rid: (
            parse_date(rdata["start_date"]),
            parse_date(rdata["end_date"]),
        )
        for rid, rdata in relations.items()
    }

    # node_id → list of (start, end) tuples for its member relations
    node_date_ranges: dict[int, list[tuple]] = {}
    for node_id, members in nodes.items():
        node_date_ranges[node_id] = [rel_dates[m] for m in members if m in rel_dates]

    def nodes_overlap_in_time(na: int, nb: int) -> bool:
        """Return True if any member of na overlaps in time with any member of nb."""
        for sa, ea in node_date_ranges.get(na, []):
            for sb, eb in node_date_ranges.get(nb, []):
                if dates_overlap(sa, ea, sb, eb):
                    return True
        return False

    # Rebuild way → node index after filtering
    way_to_nodes: dict[int, set[int]] = defaultdict(set)
    for rid, rdata in relations.items():
        node_id = rel_to_node[rid]
        for wid in rdata["all_ways"]:
            way_to_nodes[wid].add(node_id)

    edge_set: set[frozenset] = set()
    skipped_temporal = 0
    for wid, node_set in way_to_nodes.items():
        node_list = list(node_set)
        for i in range(len(node_list)):
            for j in range(i + 1, len(node_list)):
                na, nb = node_list[i], node_list[j]
                pair = frozenset((na, nb))
                if pair in edge_set:
                    continue
                if not nodes_overlap_in_time(na, nb):
                    skipped_temporal += 1
                    continue
                edge_set.add(pair)

    edges = [sorted(e) for e in edge_set]
    edges.sort()

    _log(
        f"  {len(edges):,} edges among {len(nodes):,} nodes "
        f"({skipped_temporal:,} non-overlapping way-sharing pairs skipped)"
    )

    # ------------------------------------------------------------------
    # Output
    # ------------------------------------------------------------------
    def _node_entry(nid: int, members: list[int]) -> dict:
        entry: dict = {"members": members}
        dropped = dropped_into.get(nid)
        if dropped:
            entry["dropped"] = dropped
        return entry

    output = {
        "nodes": {
            str(nid): _node_entry(nid, members) for nid, members in nodes.items()
        },
        "edges": edges,
    }

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    _log(f"Wrote graph to {args.output}")


if __name__ == "__main__":
    main()
