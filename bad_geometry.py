#!/usr/bin/env python
"""Find relations with geometries that are broken in various ways."""

import argparse
import csv
import random
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import osmium
import osmium.filter
from osmium.osm.types import Relation
from shapely.validation import explain_validity
from tqdm import tqdm

import geometry


@dataclass
class RelationGeom:
    outer: list[int]
    inner: list[int]


class RelGeomCollector(osmium.SimpleHandler):
    """Pass 1: collect tags and outer/inner way member IDs for target relations."""

    def __init__(self):
        super().__init__()
        self.relations: dict[int, RelationGeom] = {}

    def relation(self, r: Relation) -> None:
        outer = [m.ref for m in r.members if m.type == "w" and m.role in ("", "outer")]
        inner = [m.ref for m in r.members if m.type == "w" and m.role == "inner"]
        self.relations[r.id] = RelationGeom(outer=outer, inner=inner)


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
        if valid:
            self.way_nodes[w.id] = [v[0] for v in valid]
            self.way_coords[w.id] = [(v[1], v[2]) for v in valid]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Find invalid geometries in an OSM PBF file."
    )
    parser.add_argument("osm_file", help="Path to the .osm.pbf file")
    parser.add_argument(
        "--ids",
        type=str,
        help="Comma-separated list of relation IDs to consider "
        "(default is all named relations)",
    )
    parser.add_argument("--output_dir", default=".")

    args = parser.parse_args()
    target_ids = []
    if args.ids:
        target_ids = [int(id) for id in args.ids.split(",")]

    # Pass 1: collect relation tags and member way IDs
    rel_collector = RelGeomCollector()
    rel_collector.apply_file(
        args.osm_file,
        filters=[osmium.filter.IdFilter(target_ids)]
        if target_ids
        else [osmium.filter.KeyFilter("boundary")],
    )

    # Gather all way IDs referenced by the target relations
    all_way_ids: set[int] = set()
    for rel in rel_collector.relations.values():
        all_way_ids.update(rel.outer)
        all_way_ids.update(rel.inner)

    print(
        f"Loaded {len(rel_collector.relations)} relation(s) referencing {len(all_way_ids)} ways."
    )

    # Pass 2: collect way coordinates (requires locations=True)
    way_collector = WayCoordCollector(all_way_ids)
    way_collector.apply_file(
        args.osm_file, filters=[osmium.filter.IdFilter(all_way_ids)], locations=True
    )

    way_nodes = way_collector.way_nodes
    way_coords = way_collector.way_coords

    warning_map = {
        geometry.OpenRingWarning: "nonclosed-ring",
        geometry.UncontainedInnerRingWarning: "uncontained-inner-ring",
        geometry.MissingWayWarning: "invalid-way-reference",
        "Nested shells": "nested-shells",
        "Ring Self-intersection": "ring-self-intersect",
        "Self-intersection": "self-intersect",
    }

    by_type = defaultdict[str, list[tuple[int, str]]](list)
    n_valid = 0
    n_invalid = 0
    rids = [*rel_collector.relations.keys()]
    random.shuffle(rids)
    for rid in tqdm(rids, smoothing=0):
        geom = rel_collector.relations[rid]
        rings, warnings = geometry.build_polygon_rings(
            geom.outer, geom.inner, way_nodes, way_coords
        )
        if warnings:
            types = {type(warning) for warning in warnings}
            for typ in types:
                by_type[warning_map[typ]].append(
                    (rid, ", ".join(str(w) for w in warnings if isinstance(w, typ)))
                )
            n_invalid += 1
            continue
        poly = geometry.shapely_polygon_from_rings(rings, way_coords)
        if not poly:
            by_type["no-shapely"].append((rid, ""))
            n_invalid += 1
            continue

        if not poly.is_valid:
            reason = explain_validity(poly)
            error_type = reason.split("[")[0]  # strip out any coords
            error_code = warning_map.get(error_type, "other")
            by_type[error_code].append((rid, reason))
            n_invalid += 1
            continue

        n_valid += 1

    out_dir = Path(args.output_dir)

    with open(out_dir / "bad_geometry.summary.csv", "w") as f:
        out = csv.DictWriter(f, fieldnames=["type", "count"])
        out.writeheader()
        out.writerow({"type": "valid", "count": n_valid})  # is str() needed?
        out.writerow({"type": "invalid", "count": n_invalid})
        out.writerows({"type": typ, "count": len(rs)} for typ, rs in by_type.items())

    for typ, rs in by_type.items():
        with open(out_dir / f"{typ}.examples.txt", "w") as f:
            examples = rs if len(rs) < 1_000 else random.sample(rs, 1_000)
            f.writelines(f"{rid}: {problems}\n" for rid, problems in examples)


if __name__ == "__main__":
    main()
