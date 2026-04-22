#!/usr/bin/env python3
"""
Convert WHM countries.json to OSM PBF format.

Reads whm/countries.json, projects SVG paths to lat/lon (Winkel Tripel +
correction mesh), optionally clips to land, then writes an OSM PBF using the
shared-topology pipeline from geojson_to_osm.py (nodes and ways are
deduplicated so adjacent countries share the same way objects along their
common border).

Usage:
    # Sample: Central Europe at AD 2014
    python whm_to_osm.py --year 2014 \\
        --ids 30439612-germany 30476001-france 30439631-poland \\
               30439606-czech 30439597-austria 30439646-switzerland \\
               30439599-belgium 30439629-netherlands \\
        -o central_europe_2014.osm.pbf

    # All 219 countries at AD 2014
    python whm_to_osm.py --year 2014 -o whm_2014.osm.pbf

    # All data across all years (produces chronology relations)
    python whm_to_osm.py -o whm_all.osm.pbf
"""

import argparse
import json
import sys
from pathlib import Path

from tqdm import tqdm

import geojson_to_osm as g2o
from whm.unproject import _clip_to_land, _load_land, parse_svg_path, rings_to_geometry

COUNTRIES_JSON = Path(__file__).parent / "countries.json"
LAND_GEOJSON = Path(__file__).parent / "land.geojson"


# ── Temporal helpers ───────────────────────────────────────────────────────────


def _fmt_year(year: int) -> str:
    """Format an astronomical year as a zero-padded OSM date string.

    Examples: 2014 → '2014', 100 → '0100', -23 → '-0023', 0 → '0000'
    """
    if year < 0:
        return f"-{abs(year):04d}"
    return f"{year:04d}"


def all_states(segments: list[dict]) -> list[dict]:
    """Reconstruct the full property state for every segment.

    Segments carry only *changed* properties, so we accumulate them in
    chronological order to produce a full snapshot for each segment.
    """
    result: list[dict] = []
    state: dict = {}
    for seg in segments:
        state = {**state, **seg}
        result.append(state)
    return result


def extract_base_name(title: str) -> str:
    """Extract the entity name from a WHM title.

    Takes everything before the first comma:
      'Egypt, Old Kingdom, 2925 - c2150BCE'  →  'Egypt'
      'Uruk, c2900 - 2335BCE.'               →  'Uruk'
    """
    return title.split(",")[0].strip()


def state_at_year(segments: list[dict], year: int) -> dict | None:
    """Reconstruct the full property state for an entity at the given year.

    Segments carry only *changed* properties (fill, path, title), so we
    accumulate them in chronological order until we hit the one whose range
    covers `year`.

    Returns None if the entity is not active at `year`.
    """
    state: dict = {}
    for seg in segments:
        if seg["start_date"] > year:
            break  # all remaining segments start later
        for k, v in seg.items():
            if k not in ("start_date", "end_date"):
                state[k] = v
        if seg["end_date"] >= year:
            # Include the active segment's own date range
            state["start_date"] = seg["start_date"]
            state["end_date"] = seg["end_date"]
            return state
    return None  # year falls in a gap between segments


# ── Projection / geometry helpers ─────────────────────────────────────────────


def project_path(path_d: str) -> dict | None:
    """Project an SVG d= string to a GeoJSON geometry dict (Winkel Tripel + mesh)."""
    rings = parse_svg_path(path_d)
    return rings_to_geometry(rings)


def drop_holes(geom: dict) -> dict:
    """Strip inner rings (holes) from a Polygon or MultiPolygon geometry.

    geojson_to_osm.py only handles outer rings; holes can arise when the land
    mask excludes enclosed water bodies (e.g. the Caspian Sea from Kazakhstan).
    """
    if geom["type"] == "Polygon":
        return {"type": "Polygon", "coordinates": geom["coordinates"][:1]}
    if geom["type"] == "MultiPolygon":
        return {
            "type": "MultiPolygon",
            "coordinates": [[poly[0]] for poly in geom["coordinates"]],
        }
    return geom


# ── Main ───────────────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert a WHM year-slice to OSM PBF via shared-topology extraction"
    )
    parser.add_argument(
        "--year",
        type=int,
        default=None,
        help="Astronomical year to export (omit to export all years; use 0 for 1 BC, -1 for 2 BC, …)",
    )
    parser.add_argument(
        "--ids",
        nargs="+",
        metavar="ID",
        help="Only process these path IDs (e.g. 30439612-germany); default: all active",
    )
    parser.add_argument(
        "--clip-land",
        type=Path,
        default=LAND_GEOJSON,
        metavar="GEOJSON",
        help=f"Land mask for clipping coastlines (default: {LAND_GEOJSON})",
    )
    parser.add_argument(
        "--no-clip",
        action="store_true",
        help="Skip land clipping (faster, but coastlines will be wrong)",
    )
    parser.add_argument(
        "--countries-json",
        type=Path,
        default=COUNTRIES_JSON,
        help=f"Input countries.json (default: {COUNTRIES_JSON})",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("out.osm.pbf"),
        help="Output OSM PBF file (default: out.osm.pbf)",
    )
    args = parser.parse_args()

    # ── Load countries ─────────────────────────────────────────────────────────
    print(f"Loading {args.countries_json} …")
    all_entities: dict[str, list] = json.loads(args.countries_json.read_text())

    id_filter = set(args.ids) if args.ids else None
    if id_filter:
        all_entities = {k: v for k, v in all_entities.items() if k in id_filter}
        print(f"  Filtered to {len(all_entities)} requested IDs")
    else:
        print(f"  {len(all_entities):,} total IDs")

    # ── Land mask ──────────────────────────────────────────────────────────────
    land_tree = land_geoms = None
    if not args.no_clip:
        if args.clip_land.exists():
            print(f"Loading land mask {args.clip_land} …")
            land_tree, land_geoms = _load_land(args.clip_land)
        else:
            print(f"Warning: land mask {args.clip_land} not found; skipping clip.")

    # ── Project and clip entities ─────────────────────────────────────────────

    def _make_feature(pid: str, state: dict) -> dict | None:
        """Project, clip, and wrap one entity state as a GeoJSON Feature."""
        geom = project_path(state["path"])
        if geom is None:
            return None
        if land_tree is not None:
            geom = _clip_to_land(geom, land_tree, land_geoms)
            if geom is None:
                return None
        geom = drop_holes(geom)
        name = pid.split("-", 1)[1] if "-" in pid else pid
        props: dict = {
            "type": "boundary",
            "boundary": "administrative",
            "admin_level": "2",
            "name": state.get("title") or name,
            "whmid": pid,
            "start_date": _fmt_year(state["start_date"]),
            "end_date": _fmt_year(state["end_date"]),
            "group": state.get("type"),
        }
        if state.get("fill"):
            props["fill"] = state["fill"]
        return {"type": "Feature", "geometry": geom, "properties": props}

    features: list[dict] = []
    chronology_relations: list[dict] = []

    if args.year is not None:
        # ── Single-year mode ──────────────────────────────────────────────────
        n_active = 0
        for pid, segments in all_entities.items():
            state = state_at_year(segments, args.year)
            if state is None or not state.get("path"):
                continue
            n_active += 1
            feat = _make_feature(pid, state)
            if feat is None:
                continue
            features.append(feat)

        print(f"Year {args.year}: {n_active} active → {len(features)} features")

    else:
        # ── All-years mode ────────────────────────────────────────────────────
        n_segments = n_with_path = 0
        print("Extracting features…")
        for pid, segments in tqdm(all_entities.items()):
            pid_feat_indices: list[int] = []
            for state in all_states(segments):
                if not state.get("path"):
                    continue
                n_segments += 1
                feat = _make_feature(pid, state)
                if feat is None:
                    continue
                n_with_path += 1
                pid_feat_indices.append(len(features))
                features.append(feat)

            if len(pid_feat_indices) > 1:
                first_title = features[pid_feat_indices[0]]["properties"].get(
                    "name", ""
                )
                chronology_relations.append(
                    {
                        "tags": {
                            "type": "chronology",
                            "whmid": pid,
                            "name": extract_base_name(first_title),
                        },
                        "member_feat_indices": pid_feat_indices,
                    }
                )

        print(
            f"All years: {n_segments} segments with path"
            f" → {len(features)} features"
            f", {len(chronology_relations)} chronology relations"
        )

    if not features:
        print("No features to write; exiting.")
        sys.exit(0)

    # ── Build topology and write OSM PBF ──────────────────────────────────────
    print("Building node index…")
    node_map, feature_rings = g2o.build_node_index(features)
    print(f"  {len(node_map):,} unique nodes")

    print("Finding junction nodes…")
    junctions = g2o.find_junctions(feature_rings)
    print(f"  {len(junctions):,} junction nodes")

    print("Building and deduplicating ways…")
    way_map, feature_way_refs = g2o.build_ways(feature_rings, junctions)
    print(f"  {len(way_map):,} unique ways")

    print("Removing spur ways…")
    way_map, feature_way_refs = g2o.remove_spur_ways(way_map, feature_way_refs)
    print(f"  {len(way_map):,} ways after spur removal")

    print(f"Writing {args.output}…")
    g2o.write_osm(
        str(args.output),
        features,
        node_map,
        way_map,
        feature_way_refs,
        chronology_relations=chronology_relations or None,
    )
    print("Done.")


if __name__ == "__main__":
    main()
