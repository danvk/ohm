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
import html as html_lib
import json
import sys
from pathlib import Path

from tqdm import tqdm

import geojson_to_osm as g2o
from whm.title import parse_whm_title
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


def build_chronologies(
    name_to_entries: dict[str, list[tuple[int, int, str]]],
    features: list[dict],
) -> list[dict]:
    """Build chronology relations grouped by parsed feature name.

    Features sharing the same name (even across different WHM IDs) are linked
    in chronological order, producing more complete historical sequences than
    per-ID grouping alone. Returns a list of relation dicts ready for g2o.write_osm.
    """
    relations: list[dict] = []
    n_single_pid = n_multi_pid = 0
    for name, entries in sorted(name_to_entries.items()):
        if len(entries) < 2:
            continue
        entries.sort(key=lambda e: e[0])  # sort by start_date
        feat_indices = [e[1] for e in entries]
        unique_pids = {e[2] for e in entries}
        tags = {"type": "chronology", "name": name}
        if len(unique_pids) == 1:
            tags["whmid"] = next(iter(unique_pids))
            n_single_pid += 1
        else:
            n_multi_pid += 1
        relations.append({"tags": tags, "member_feat_indices": feat_indices})

    print(
        f"  {len(relations)} chronology relations"
        f" ({n_single_pid} single-ID, {n_multi_pid} cross-ID)"
    )

    if n_multi_pid > 0:
        multi_pid_chrons = [
            c
            for c in relations
            if len(
                {features[i]["properties"]["whmid"] for i in c["member_feat_indices"]}
            )
            > 1
        ]
        multi_pid_chrons.sort(key=lambda c: -len(c["member_feat_indices"]))
        print("\nTop cross-ID chronologies (by feature count):")
        for c in multi_pid_chrons[:10]:
            feat_count = len(c["member_feat_indices"])
            pid_count = len(
                {features[i]["properties"]["whmid"] for i in c["member_feat_indices"]}
            )
            print(f"  {c['tags']['name']!r}: {feat_count} features, {pid_count} IDs")
        print()

    return relations


def make_feature(pid: str, state: dict, land_tree, land_geoms) -> dict | None:
    """Project, clip, and wrap one entity state as a GeoJSON Feature."""
    geom = project_path(state["path"])
    if geom is None:
        return None
    if land_tree is not None:
        geom = _clip_to_land(geom, land_tree, land_geoms)
        if geom is None:
            return None
    geom = drop_holes(geom)
    fallback_name = pid.split("-", 1)[1] if "-" in pid else pid
    raw_title = state.get("title") or fallback_name
    parsed = parse_whm_title(raw_title)
    props = {
        "type": "boundary",
        "boundary": "administrative",
        "admin_level": "2",
        "name": parsed.name or fallback_name,
        "whmid": pid,
        "start_date": _fmt_year(state["start_date"]),
        "end_date": _fmt_year(state["end_date"]),
        "group": state.get("type"),
    }
    if parsed.leader:
        props["leader"] = parsed.leader
    if parsed.dynasty:
        props["dynasty"] = parsed.dynasty
    if parsed.span:
        props["span"] = parsed.span
    if parsed.note:
        props["note"] = parsed.note
    if state.get("fill"):
        props["fill"] = state["fill"]
    props["title:raw"] = raw_title
    return {"type": "Feature", "geometry": geom, "properties": props}


_WHM_VIEWER = "https://www.danvk.org/whm3/"


def write_chronology_html(
    output_path: Path,
    chronology_relations: list[dict],
    features: list[dict],
) -> None:
    """Write an HTML file listing every chronology with its member features.

    Each chronology entry shows its name, overall date range, relation count,
    and distinct WHM ID count.  Its sublist links each member feature to the
    deployed WHM boundary viewer at the feature's start date.
    """

    def esc(s: object) -> str:
        return html_lib.escape(str(s))

    def parse_date_tag(s: str) -> int:
        # "-0023" → -23, "0100" → 100
        return -int(s[1:]) if s.startswith("-") else int(s)

    # Pair each chronology with its OSM relation ID before sorting.
    # Chronology at index chron_idx gets OSM ID len(features) + chron_idx + 1.
    indexed = [
        (len(features) + chron_idx + 1, chron)
        for chron_idx, chron in enumerate(chronology_relations)
    ]
    indexed.sort(
        key=lambda x: parse_date_tag(
            features[x[1]["member_feat_indices"][0]]["properties"]["start_date"]
        )
    )

    lines = [
        "<!doctype html>",
        '<html lang="en">',
        "<head>",
        '<meta charset="utf-8">',
        "<title>WHM Chronologies</title>",
        "</head>",
        "<body>",
        "<h1>WHM Chronologies</h1>",
        f"<p>{len(chronology_relations):,} chronologies</p>",
        "<ol>",
    ]

    for chron_osm_id, chron in indexed:
        name = chron["tags"]["name"]
        feat_indices = chron["member_feat_indices"]
        chron_start = features[feat_indices[0]]["properties"]["start_date"]
        chron_end = features[feat_indices[-1]]["properties"]["end_date"]
        n_relations = len(feat_indices)
        n_pids = len({features[i]["properties"]["whmid"] for i in feat_indices})

        lines.append(
            f'<li id="{chron_osm_id}"><b>{esc(name)}</b>'
            f" ({esc(chron_start)}–{esc(chron_end)},"
            f" {n_relations} relations, {n_pids} WHM IDs)"
        )
        lines.append("<ol>")
        for feat_idx in feat_indices:
            props = features[feat_idx]["properties"]
            osm_id = feat_idx + 1
            start_date = props["start_date"]
            end_date = props["end_date"]
            raw_title = props.get("title:raw", "")
            url = f"{_WHM_VIEWER}?ids={osm_id}&date={start_date}"
            lines.append(
                f'<li><a href="{esc(url)}" target="_blank">'
                f"{esc(start_date)}–{esc(end_date)}</a>"
                f" {esc(raw_title)}</li>"
            )
        lines.append("</ol></li>")

    lines += ["</ol>", "</body>", "</html>"]
    output_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {output_path}")


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
            feat = make_feature(pid, state, land_tree, land_geoms)
            if feat is None:
                continue
            features.append(feat)

        print(f"Year {args.year}: {n_active} active → {len(features)} features")

    else:
        # ── All-years mode ────────────────────────────────────────────────────
        n_segments = n_with_path = 0
        print("Extracting features…")

        # name → list of (start_date, feature_index, pid)
        name_to_entries: dict[str, list[tuple[int, int, str]]] = {}

        for pid, segments in tqdm(all_entities.items()):
            for state in all_states(segments):
                if not state.get("path"):
                    continue
                n_segments += 1
                feat = make_feature(pid, state, land_tree, land_geoms)
                if feat is None:
                    continue
                n_with_path += 1
                feat_idx = len(features)
                features.append(feat)
                feat_name = feat["properties"].get("name") or ""
                if feat_name:
                    name_to_entries.setdefault(feat_name, []).append(
                        (state["start_date"], feat_idx, pid)
                    )

        print(f"All years: {n_segments} segments with path → {len(features)} features")
        chronology_relations = build_chronologies(name_to_entries, features)

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

    if chronology_relations:
        stem = args.output.name.split(".")[0]
        html_path = args.output.with_name(stem + ".html")
        write_chronology_html(html_path, chronology_relations, features)

    print("Done.")


if __name__ == "__main__":
    main()
