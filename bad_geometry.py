#!/usr/bin/env python
"""Find relations with geometries that are broken in various ways."""

import argparse
import math
import random
import re
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

import osmium
import osmium.filter
import osmium.io
from osmium.osm.types import Relation
from shapely.validation import explain_validity
from tqdm import tqdm

import geometry
from dates import duration_years, parse_ohm_date, start_of_date
from earth_coverage import EARTH_LAND_AREA_KM2, area_km2
from stats import write_stats


@dataclass
class RelationGeom:
    outer: list[int]
    inner: list[int]
    start_date: str | None
    end_date: str | None
    name: str | None


class RelGeomCollector(osmium.SimpleHandler):
    """Pass 1: collect tags and outer/inner way member IDs for target relations."""

    def __init__(self):
        super().__init__()
        self.relations: dict[int, RelationGeom] = {}

    def relation(self, r: Relation) -> None:
        outer = [m.ref for m in r.members if m.type == "w" and m.role in ("", "outer")]
        inner = [m.ref for m in r.members if m.type == "w" and m.role == "inner"]
        self.relations[r.id] = RelationGeom(
            outer=outer,
            inner=inner,
            start_date=r.tags.get("start_date"),
            end_date=r.tags.get("end_date"),
            name=r.tags.get("name:en") or r.tags.get("name"),
        )


class WayNodeCollector(osmium.SimpleHandler):
    """Pass 2: collect node ID lists for target ways (no location resolution)."""

    def __init__(self, way_ids: set[int]):
        super().__init__()
        self._way_ids = way_ids
        self.way_nodes: dict[int, list[int]] = {}

    def way(self, w: Any) -> None:
        if w.id not in self._way_ids:
            return
        node_ids = [n.ref for n in w.nodes]
        if node_ids:
            self.way_nodes[w.id] = node_ids


class NodeCoordCollector(osmium.SimpleHandler):
    """Pass 3: collect (lon, lat) for specific node IDs."""

    def __init__(self, node_ids: set[int]):
        super().__init__()
        self._node_ids = node_ids
        self.node_coords: dict[int, tuple[float, float]] = {}

    def node(self, n: Any) -> None:
        if n.id in self._node_ids and n.location.valid():
            self.node_coords[n.id] = (n.location.lon, n.location.lat)


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

    # Pass 2: collect node ID lists for target ways (no location resolution needed)
    way_node_collector = WayNodeCollector(all_way_ids)
    way_node_collector.apply_file(
        args.osm_file, filters=[osmium.filter.IdFilter(all_way_ids)]
    )

    # Gather all node IDs referenced by the target ways
    all_node_ids: set[int] = set()
    for nodes in way_node_collector.way_nodes.values():
        all_node_ids.update(nodes)

    print(
        f"  Ways reference {len(all_node_ids)} unique nodes."
    )

    # Pass 3: collect coordinates for only those nodes (no planet-scale location cache)
    node_coord_collector = NodeCoordCollector(all_node_ids)
    node_coord_collector.apply_file(
        args.osm_file, filters=[osmium.filter.IdFilter(all_node_ids)]
    )

    node_coords = node_coord_collector.node_coords
    way_nodes = way_node_collector.way_nodes
    # Reconstruct way_coords from the per-node coordinate map
    way_coords: dict[int, list[tuple[float, float]]] = {}
    for wid, nids in way_nodes.items():
        coords = [node_coords[nid] for nid in nids if nid in node_coords]
        if coords:
            way_coords[wid] = coords
        # Also filter way_nodes to only valid nodes (matching original WayCoordCollector)
        valid_nids = [nid for nid in nids if nid in node_coords]
        if valid_nids:
            way_nodes[wid] = valid_nids
        else:
            del way_nodes[wid]

    # Read the planet timestamp from the PBF header to use as default end_date.
    with osmium.io.Reader(args.osm_file) as r:
        timestamp_str = r.header().get("timestamp") or ""
    m = re.search(r"(\d{4}-\d{2}-\d{2})", timestamp_str)
    planet_date = start_of_date(parse_ohm_date(m.group(1))) if m else (2026, 1, 1)

    warning_map = {
        geometry.OpenRingWarning: "nonclosed-ring",
        geometry.UncontainedInnerRingWarning: "uncontained-inner-ring",
        geometry.MissingWayWarning: "invalid-way-reference",
        "Nested shells": "nested-shells",
        "Ring Self-intersection": "ring-self-intersect",
        "Self-intersection": "self-intersect",
    }

    # raw_examples: error_code → [(earth_years, ftype, fid, problem_str)]
    raw_examples: dict[str, list[tuple[float, str, int, str]]] = defaultdict(list)
    n_valid = 0
    n_invalid = 0
    rids = [*rel_collector.relations.keys()]
    random.shuffle(rids)
    for rid in tqdm(rids, smoothing=0):
        geom = rel_collector.relations[rid]
        rings, poly_warnings = geometry.build_polygon_rings(
            geom.outer, geom.inner, way_nodes, way_coords
        )

        poly = geometry.shapely_polygon_from_rings(rings, way_coords)

        # Compute earth-years using a valid (or make_valid'd) polygon.
        earth_years = 0.0
        if poly is not None:
            start_date = parse_ohm_date(geom.start_date)
            if start_date is not None:
                end_date = parse_ohm_date(geom.end_date)
                end_pt = (
                    start_of_date(end_date) if end_date is not None else planet_date
                )
                dur = duration_years((start_of_date(start_date), end_pt))
                if math.isfinite(dur) and dur >= 0:
                    # Pass poly directly even if invalid: area_km2 uses
                    # shapely.transform which works on invalid geometries and
                    # gives a good approximation (slightly off only for
                    # self-intersecting rings, which is acceptable for ranking).
                    earth_years = dur * area_km2(poly) / EARTH_LAND_AREA_KM2

        has_problem = False

        for typ in {type(w) for w in poly_warnings}:
            raw_examples[warning_map[typ]].append(
                (
                    earth_years,
                    "r",
                    rid,
                    (geom.name or "")
                    + " "
                    + ", ".join(str(w) for w in poly_warnings if isinstance(w, typ)),
                )
            )
            has_problem = True

        if poly is None:
            raw_examples["no-shapely"].append((earth_years, "r", rid, ""))
            has_problem = True
        elif not poly_warnings and not poly.is_valid:
            # avoid generating shapely warnings for polygons we've "fixed" ourselves
            reason = explain_validity(poly)
            error_type = reason.split("[")[0]  # strip out any coords
            error_code = warning_map.get(error_type, "other")
            message = (geom.name or "") + " " + reason
            raw_examples[error_code].append((earth_years, "r", rid, message))
            has_problem = True

        if has_problem:
            n_invalid += 1
        else:
            n_valid += 1

    # Sort each bucket by earth-years descending, then build the final by_type.
    by_type: dict[str, list[tuple[str, int, str]]] = {}
    for typ, items in raw_examples.items():
        items.sort(key=lambda x: (-x[0], x[2]))
        by_type[typ] = [
            (
                "r",
                fid,
                f"({ey:.4f}ey) {problem}" if problem else f"{ey:.4f} earth-yr",
            )
            for ey, _, fid, problem in items
        ]

    write_stats(
        args.output_dir,
        "bad_geometry",
        by_type,
        {
            "geom-valid": n_valid,
            "geom-invalid": n_invalid,
        },
        preserve_sort_order=True,
    )


if __name__ == "__main__":
    main()
