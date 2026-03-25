import argparse
import math
from collections import Counter, defaultdict
from typing import Any

import osmium
import osmium.filter
from osmium.osm.types import Relation

from geometry import build_polygon_rings, ring_coords

IGNORE_KEY_PREFIXES = [
    "wikipedia",
    "source",
    "fixme",
]

# Tolerance fraction: max allowed node displacement as a fraction of total ring
# perimeter. At 1%, a 5.8° Bundou boundary tolerates ~0.058° ≈ 6 km rounding,
# giving precision=3 (110 m). A 0.006° short segment tolerates ~0.00006°,
# giving precision=5 (1.1 m), so genuinely distinct short segments are kept
# separate while duplicated large boundaries with ~10 m node displacement are
# still detected as duplicates.
_TOLERANCE_FRACTION = 0.01


class DupeCandidateFinder(osmium.SimpleHandler):
    def __init__(self):
        super(DupeCandidateFinder, self).__init__()
        self.name_to_relation = defaultdict[tuple, list[int]](list)

    def relation(self, r: Relation) -> None:
        name = r.tags.get("name")
        if not name:
            return
        if len(r.members) == 0:
            return  # could remove this, but these are the more problematic ones
        tags = [
            (tag.k, tag.v)
            for tag in r.tags
            if not any(tag.k.startswith(prefix) for prefix in IGNORE_KEY_PREFIXES)
        ]
        tags.sort()
        self.name_to_relation[tuple(tags)].append(r.id)


class RelGeomCollector(osmium.SimpleHandler):
    """Pass 1: collect tags and outer/inner way member IDs for target relations."""

    def __init__(self, target_ids: set[int]):
        super().__init__()
        self._target_ids = target_ids
        # rel_id → {"tags": [...], "outer": [...], "inner": [...]}
        self.relations: dict[int, dict] = {}

    def relation(self, r: Relation) -> None:
        if r.id not in self._target_ids:
            return
        tags = [
            (tag.k, tag.v)
            for tag in r.tags
            if not any(tag.k.startswith(prefix) for prefix in IGNORE_KEY_PREFIXES)
        ]
        tags.sort()
        outer = [m.ref for m in r.members if m.type == "w" and m.role != "inner"]
        inner = [m.ref for m in r.members if m.type == "w" and m.role == "inner"]
        self.relations[r.id] = {
            "tags": tuple(tags),
            "outer": outer,
            "inner": inner,
        }


class WayCoordCollector(osmium.SimpleHandler):
    """Pass 2 (locations=True): collect (lon, lat) coords for target ways."""

    def __init__(self, way_ids: set[int]):
        super().__init__()
        self._way_ids = way_ids
        self.way_nodes: dict[int, list[int]] = {}
        self.way_coords: dict[int, list[tuple[float, float]]] = {}

    def way(self, w: Any) -> None:
        if w.id not in self._way_ids:
            return
        valid = [(n.ref, n.lon, n.lat) for n in w.nodes if n.location.valid()]
        if len(valid) >= 2:
            self.way_nodes[w.id] = [v[0] for v in valid]
            self.way_coords[w.id] = [(v[1], v[2]) for v in valid]


def geometry_key(
    outer: list[int],
    inner: list[int],
    way_nodes: dict[int, list[int]],
    way_coords: dict[int, list[tuple[float, float]]],
) -> frozenset[tuple[float, float]]:
    """Return a canonical frozenset of rounded (lon, lat) pairs for a relation's geometry.

    Two relations with identical underlying coordinates but different member
    ways will produce the same key. Rounding precision scales with feature size:
    larger features use coarser rounding to absorb small node-placement
    differences, while small features use finer rounding to stay distinct.
    """
    polygons = build_polygon_rings(outer, inner, way_nodes, way_coords)

    # Measure total perimeter in degrees across all rings.
    total_length = 0.0
    all_pts_per_ring: list[list[tuple[float, float]]] = []
    for polygon in polygons:
        for ring in polygon:
            pts = list(ring_coords(ring, way_coords))
            all_pts_per_ring.append(pts)
            for i in range(len(pts) - 1):
                dx = pts[i + 1][0] - pts[i][0]
                dy = pts[i + 1][1] - pts[i][1]
                total_length += math.sqrt(dx * dx + dy * dy)

    # Derive precision: round to the scale of _TOLERANCE_FRACTION * perimeter.
    if total_length > 0:
        precision = max(3, math.ceil(-math.log10(total_length * _TOLERANCE_FRACTION)))
    else:
        precision = 6

    pts_set: set[tuple[float, float]] = set()
    for pts in all_pts_per_ring:
        for lon, lat in pts:
            pts_set.add((round(lon, precision), round(lat, precision)))
    return frozenset(pts_set)


class DupeFinder(osmium.SimpleHandler):
    def __init__(self):
        super(DupeFinder, self).__init__()
        self.key_to_id = defaultdict[tuple, list[int]](list)

    def relation(self, r: Relation) -> None:
        key = relation_key(r)
        self.key_to_id[key].append(r.id)


def relation_key(r: Relation) -> tuple:
    tags = [
        (tag.k, tag.v)
        for tag in r.tags
        if not any(tag.k.startswith(prefix) for prefix in IGNORE_KEY_PREFIXES)
    ]
    tags.sort()
    members = [(m.role, m.type, m.ref) for m in r.members]
    members.sort()
    return (tuple(tags), tuple(members))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Find elements in an OSM PBF file by name."
    )
    parser.add_argument("osm_file", help="Path to the .osm.pbf file")

    args = parser.parse_args()

    candidate_handler = DupeCandidateFinder()
    candidate_handler.apply_file(
        args.osm_file, filters=[osmium.filter.KeyFilter("name")]
    )

    ids = [
        id
        for ids in candidate_handler.name_to_relation.values()
        for id in ids
        if len(ids) >= 2
    ]

    # target_ids = [2879823, 2879817, 2879806]
    # target_ids = [2795077, 2796058]
    # target_ids = [2902554, 2902565]
    target_ids = ids

    print("Candidate IDs:", len(target_ids))

    # Pass 1: collect relation tags and member way IDs
    rel_collector = RelGeomCollector(set(target_ids))
    rel_collector.apply_file(
        args.osm_file, filters=[osmium.filter.IdFilter(target_ids)]
    )
    # print(rel_collector.relations)

    # Gather all way IDs referenced by the target relations
    all_way_ids: set[int] = set()
    for rel in rel_collector.relations.values():
        all_way_ids.update(rel["outer"])
        all_way_ids.update(rel["inner"])

    # Pass 2: collect way coordinates (requires locations=True)
    way_collector = WayCoordCollector(all_way_ids)
    way_collector.apply_file(
        args.osm_file, filters=[osmium.filter.IdFilter(all_way_ids)], locations=True
    )

    # Build geometry keys and group relations
    geom_key_to_ids: dict = defaultdict(list)
    for rel_id, rel in rel_collector.relations.items():
        gkey = geometry_key(
            rel["outer"],
            rel["inner"],
            way_collector.way_nodes,
            way_collector.way_coords,
        )
        geom_key_to_ids[(rel["tags"], gkey)].append(rel_id)
        # print(f"{rel_id}\n{gkey}\n")

    by_count = Counter[int]()
    total_dupes = 0
    for (tags, _gkey), rel_ids in geom_key_to_ids.items():
        if len(rel_ids) < 2:
            continue
        by_count[len(rel_ids)] += 1
        total_dupes += len(rel_ids) - 1
        name = next((v for k, v in tags if k == "name"), "<unknown>")
        print(f"{name}: {len(rel_ids)} dupes:")
        for rel_id in rel_ids:
            print(f"  {rel_id} https://www.openhistoricalmap.org/relation/{rel_id}")

    print(f"Total dupes: {total_dupes}")


if __name__ == "__main__":
    main()
