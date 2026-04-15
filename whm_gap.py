#!/usr/bin/env python3
"""Compute WHM vs OHM coverage gap in earth-years.

For each WHM boundary feature, calculates how much of its (area × time) is
NOT covered by any OHM admin_level=2 feature.  Features are read from the
pre-extracted JSON files produced by extract_for_web.py, so the 1 GB OHM
planet PBF is not re-read.

Outputs two CSVs sorted by uncovered earth-years (descending):
  whm_gap_by_feature.csv    – one row per WHM relation
  whm_gap_by_chronology.csv – aggregated by whmid across all time-slices

Usage:
    uv run whm_gap.py \\
        --ohm-dir /Users/danvk/code/ohmdash/boundary \\
        --whm-dir /Users/danvk/code/ohmdash/whm-boundary \\
        --output-dir /tmp/whm_gap
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

import shapely
from shapely.geometry import MultiPolygon, Polygon
from shapely.ops import unary_union
from shapely.strtree import STRtree
from tqdm import tqdm

from dates import DateTuple, parse_ohm_date, start_of_date, to_fractional_year
from earth_coverage import EARTH_LAND_AREA_KM2, area_km2

# ── Coordinate helpers ────────────────────────────────────────────────────────

# extract_for_web.py uses:
#   quantize(lng, lat) = (round((lng+180)/360*4_000_000), round((lat+90)/180*2_000_000))
_LNG_SCALE = 4_000_000 / 360
_LAT_SCALE = 2_000_000 / 180


def _unquantize(x: int, y: int) -> tuple[float, float]:
    lng = x / _LNG_SCALE - 180
    lat = y / _LAT_SCALE - 90
    return lng, lat


def _decode_way(deltas: list[int]) -> list[tuple[float, float]]:
    """Delta-decode a quantized way into (lng, lat) float pairs."""
    coords: list[tuple[float, float]] = []
    x = deltas[0]
    y = deltas[1]
    coords.append(_unquantize(x, y))
    for i in range(2, len(deltas), 2):
        x += deltas[i]
        y += deltas[i + 1]
        coords.append(_unquantize(x, y))
    return coords


def _assemble_ring(
    signed_way_ids: list[int],
    ways: dict[str, list[tuple[float, float]]],
) -> list[tuple[float, float]]:
    """Concatenate ways (reversing if negative) into a ring coordinate list.

    Adjacent ways share an endpoint; we skip the duplicate between segments
    (same approach as geometry.py:ring_coords).
    """
    coords: list[tuple[float, float]] = []
    for i, wid in enumerate(signed_way_ids):
        key = str(abs(wid))
        wcoords = ways.get(key)
        if not wcoords:
            continue
        if wid < 0:
            wcoords = list(reversed(wcoords))
        if i == 0:
            coords.extend(wcoords)
        else:
            coords.extend(wcoords[1:])
    return coords


def _build_geometry(
    rel_ways: list[list[list[int]]],
    ways: dict[str, list[tuple[float, float]]],
) -> Polygon | MultiPolygon | None:
    """Build a Shapely geometry from a relation's ways structure.

    rel_ways is a list of polygons; each polygon is a list of rings; the first
    ring is the outer boundary and subsequent rings are holes.
    """
    polys: list[Polygon] = []
    for rings in rel_ways:
        if not rings:
            continue
        outer_coords = _assemble_ring(rings[0], ways)
        if len(outer_coords) < 3:
            continue
        holes = [_assemble_ring(r, ways) for r in rings[1:] if r]
        holes = [h for h in holes if len(h) >= 3]
        try:
            poly = Polygon(outer_coords, holes)
        except Exception:
            continue
        if not poly.is_valid:
            poly = poly.buffer(0)
        if poly.is_empty:
            continue
        # buffer(0) can promote an invalid Polygon to a MultiPolygon
        if isinstance(poly, MultiPolygon):
            polys.extend(poly.geoms)
        else:
            polys.append(poly)

    if not polys:
        return None
    if len(polys) == 1:
        return polys[0]
    return MultiPolygon(polys)


# ── Data structures ───────────────────────────────────────────────────────────


@dataclass
class Feature:
    fid: int
    name: str
    start: DateTuple
    end: DateTuple
    geom: Polygon | MultiPolygon
    area_km2: float
    whmid: str = ""  # WHM only


# ── Loaders ───────────────────────────────────────────────────────────────────

# Sentinel for "still active" when end_date is absent
_ACTIVE_END: DateTuple = (2100, 1, 1)


def _parse_dates(
    tags: dict,
) -> tuple[DateTuple | None, DateTuple]:
    """Return (start, end) DateTuples from an OSM tag dict.

    Returns (None, _) if start_date is absent (feature is unusable).
    end_date defaults to _ACTIVE_END when absent.
    """
    raw_start = tags.get("start_date")
    raw_end = tags.get("end_date")

    parsed_start = parse_ohm_date(raw_start) if raw_start else None
    if parsed_start is None:
        return None, _ACTIVE_END

    start = start_of_date(parsed_start)

    if raw_end:
        parsed_end = parse_ohm_date(raw_end)
        end = start_of_date(parsed_end) if parsed_end else _ACTIVE_END
    else:
        end = _ACTIVE_END

    return start, end


def load_features(
    rel_path: Path,
    way_path: Path,
    *,
    require_whmid: bool = False,
    desc: str = "",
) -> list[Feature]:
    """Load features from extract_for_web.py JSON files."""
    print(f"Loading {desc or rel_path} …")

    with open(way_path) as f:
        raw_ways: dict[str, list[int]] = json.load(f)

    # Pre-decode all ways once
    ways: dict[str, list[tuple[float, float]]] = {
        wid: _decode_way(deltas) for wid, deltas in raw_ways.items()
    }
    print(f"  Decoded {len(ways):,} ways")

    with open(rel_path) as f:
        relations: list[dict] = json.load(f)

    features: list[Feature] = []
    n_skip_date = n_skip_geom = 0

    for rel in tqdm(relations, desc=f"  {desc or 'relations'}", unit="rel"):
        tags = rel.get("tags", {})

        # Skip chronology meta-relations
        if tags.get("type") == "chronology":
            continue
        # Only admin_level=2 boundaries
        if tags.get("boundary") != "administrative" or tags.get("admin_level") != "2":
            continue

        start, end = _parse_dates(tags)
        if start is None:
            n_skip_date += 1
            continue

        rel_ways = rel.get("ways", [])
        geom = _build_geometry(rel_ways, ways)
        if geom is None or geom.is_empty:
            n_skip_geom += 1
            continue

        km2 = area_km2(geom)
        whmid = tags.get("whmid", "") if require_whmid else tags.get("whmid", "")

        features.append(
            Feature(
                fid=rel["id"],
                name=tags.get("name", ""),
                start=start,
                end=end,
                geom=geom,
                area_km2=km2,
                whmid=whmid,
            )
        )

    print(
        f"  Loaded {len(features):,} features "
        f"(skipped {n_skip_date} no-date, {n_skip_geom} no-geometry)"
    )
    return features


# ── Gap computation ───────────────────────────────────────────────────────────


def _safe_difference(a, b):
    """Compute a.difference(b) robustly, trying progressively coarser strategies."""
    # Try exact first
    try:
        return a.difference(b)
    except Exception:
        pass
    # Make both valid and retry
    try:
        return shapely.make_valid(a).difference(shapely.make_valid(b))
    except Exception:
        pass
    # Snap to a grid (GEOS grid_size snapping resolves most topology conflicts)
    try:
        return shapely.difference(a, b, grid_size=1e-6)
    except Exception:
        pass
    # Last resort: treat as fully uncovered (return a)
    return a


def _uncovered_earth_years(
    whm: Feature,
    ohm_candidates: list[Feature],
) -> float:
    """Compute uncovered earth-years for one WHM feature against OHM candidates.

    Uses a temporal sweep: we collect all "critical times" (where the set of
    active OHM features changes) within the WHM feature's date range, then for
    each sub-interval compute the unmatched area × duration.
    """
    t_w1 = whm.start
    t_w2 = whm.end

    if not ohm_candidates:
        dur = to_fractional_year(t_w2) - to_fractional_year(t_w1)
        return whm.area_km2 * dur / EARTH_LAND_AREA_KM2

    # Collect critical times (clipped to WHM range)
    crits: list[DateTuple] = [t_w1, t_w2]
    for c in ohm_candidates:
        if t_w1 < c.start < t_w2:
            crits.append(c.start)
        if t_w1 < c.end < t_w2:
            crits.append(c.end)
    crits = sorted(set(crits))

    total_uncovered = 0.0
    for i in range(len(crits) - 1):
        t_a, t_b = crits[i], crits[i + 1]
        dur = to_fractional_year(t_b) - to_fractional_year(t_a)
        if dur <= 0:
            continue

        # OHM features active throughout [t_a, t_b]
        active = [c for c in ohm_candidates if c.start <= t_a and c.end >= t_b]

        if not active:
            total_uncovered += whm.area_km2 * dur / EARTH_LAND_AREA_KM2
        else:
            ohm_union = unary_union([c.geom for c in active])
            uncovered_geom = _safe_difference(whm.geom, ohm_union)
            if uncovered_geom is not None and not uncovered_geom.is_empty:
                km2 = area_km2(uncovered_geom)
                total_uncovered += km2 * dur / EARTH_LAND_AREA_KM2

    return total_uncovered


def compute_gap(
    whm_features: list[Feature],
    ohm_features: list[Feature],
) -> list[dict]:
    """For each WHM feature compute uncovered earth-years vs OHM.

    Returns a list of result dicts, one per WHM feature.
    """
    print(f"\nBuilding STRtree on {len(ohm_features):,} OHM geometries …")
    ohm_geoms = [f.geom for f in ohm_features]
    tree = STRtree(ohm_geoms)

    results: list[dict] = []
    n_no_candidates = 0

    for whm in tqdm(whm_features, desc="WHM features", unit="feat", smoothing=0):
        dur = to_fractional_year(whm.end) - to_fractional_year(whm.start)
        if dur <= 0:
            continue
        total_ey = whm.area_km2 * dur / EARTH_LAND_AREA_KM2

        # Spatial candidates
        spatial_idxs = tree.query(whm.geom, predicate="intersects")

        # Filter to temporal overlap
        temporal = [
            ohm_features[i]
            for i in spatial_idxs
            if ohm_features[i].start < whm.end and ohm_features[i].end > whm.start
        ]

        if not temporal:
            n_no_candidates += 1
            uncovered_ey = total_ey
        else:
            uncovered_ey = _uncovered_earth_years(whm, temporal)

        results.append(
            {
                "fid": whm.fid,
                "whmid": whm.whmid,
                "name": whm.name,
                "start_date": whm.start[0],
                "end_date": whm.end[0],
                "total_ey": total_ey,
                "uncovered_ey": uncovered_ey,
                "coverage_pct": 100.0 * (1 - uncovered_ey / total_ey) if total_ey else 0.0,
            }
        )

    print(
        f"  {n_no_candidates:,} of {len(results):,} WHM features had no OHM candidates"
        " (fully uncovered)"
    )
    return results


# ── Output ────────────────────────────────────────────────────────────────────


def _extract_base_name(title: str) -> str:
    """'Egypt, Old Kingdom, …' → 'Egypt'"""
    return title.split(",")[0].strip()


def write_by_feature(results: list[dict], out_path: Path) -> None:
    results_sorted = sorted(results, key=lambda r: r["uncovered_ey"], reverse=True)
    fieldnames = [
        "whmid", "name", "start_date", "end_date",
        "total_ey", "uncovered_ey", "coverage_pct",
    ]
    with open(out_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        for r in results_sorted:
            w.writerow(
                {
                    **r,
                    "total_ey": f"{r['total_ey']:.6f}",
                    "uncovered_ey": f"{r['uncovered_ey']:.6f}",
                    "coverage_pct": f"{r['coverage_pct']:.1f}",
                }
            )
    print(f"Wrote {len(results_sorted):,} rows → {out_path}")


def write_by_chronology(results: list[dict], out_path: Path) -> None:
    # Aggregate by whmid
    by_whmid: dict[str, dict] = {}
    for r in results:
        wid = r["whmid"] or str(r["fid"])
        if wid not in by_whmid:
            by_whmid[wid] = {
                "whmid": wid,
                "base_name": _extract_base_name(r["name"]),
                "n_segments": 0,
                "total_ey": 0.0,
                "uncovered_ey": 0.0,
            }
        by_whmid[wid]["n_segments"] += 1
        by_whmid[wid]["total_ey"] += r["total_ey"]
        by_whmid[wid]["uncovered_ey"] += r["uncovered_ey"]

    rows = sorted(by_whmid.values(), key=lambda r: r["uncovered_ey"], reverse=True)
    for row in rows:
        t = row["total_ey"]
        u = row["uncovered_ey"]
        row["coverage_pct"] = f"{100.0 * (1 - u / t):.1f}" if t else "0.0"
        row["total_ey"] = f"{t:.6f}"
        row["uncovered_ey"] = f"{u:.6f}"

    fieldnames = ["whmid", "base_name", "n_segments", "total_ey", "uncovered_ey", "coverage_pct"]
    with open(out_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote {len(rows):,} rows → {out_path}")


# ── Main ──────────────────────────────────────────────────────────────────────


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Compute WHM vs OHM coverage gap in earth-years."
    )
    ap.add_argument(
        "--ohm-dir",
        type=Path,
        default=Path("/Users/danvk/code/ohmdash/boundary"),
        help="Directory containing OHM relations2.json and ways2.json",
    )
    ap.add_argument(
        "--whm-dir",
        type=Path,
        default=Path("/Users/danvk/code/ohmdash/whm-boundary"),
        help="Directory containing WHM relations2.json and ways2.json",
    )
    ap.add_argument(
        "--output-dir",
        type=Path,
        default=Path("/tmp/whm_gap"),
        help="Directory for output CSVs (default: /tmp/whm_gap)",
    )
    ap.add_argument(
        "--limit",
        type=int,
        default=None,
        metavar="N",
        help="Process only the first N WHM features (for quick testing)",
    )
    args = ap.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)

    ohm_features = load_features(
        args.ohm_dir / "relations2.json",
        args.ohm_dir / "ways2.json",
        desc="OHM",
    )

    whm_features = load_features(
        args.whm_dir / "relations2.json",
        args.whm_dir / "ways2.json",
        require_whmid=True,
        desc="WHM",
    )

    if args.limit:
        whm_features = whm_features[: args.limit]
        print(f"(limited to first {args.limit} WHM features)")

    results = compute_gap(whm_features, ohm_features)

    write_by_feature(results, args.output_dir / "whm_gap_by_feature.csv")
    write_by_chronology(results, args.output_dir / "whm_gap_by_chronology.csv")

    # Print top 20 chronologies
    print("\nTop 20 WHM chronologies by uncovered earth-years:")
    print(f"{'base_name':<35} {'uncov_ey':>10} {'total_ey':>10} {'cov%':>6}")
    print("-" * 65)
    by_whmid: dict[str, dict] = {}
    for r in results:
        wid = r["whmid"] or str(r["fid"])
        if wid not in by_whmid:
            by_whmid[wid] = {"base_name": _extract_base_name(r["name"]), "total": 0.0, "uncov": 0.0}
        by_whmid[wid]["total"] += r["total_ey"]
        by_whmid[wid]["uncov"] += r["uncovered_ey"]
    top = sorted(by_whmid.values(), key=lambda x: x["uncov"], reverse=True)[:20]
    for row in top:
        t, u = row["total"], row["uncov"]
        pct = 100 * (1 - u / t) if t else 0
        print(f"  {row['base_name']:<33} {u:10.4f} {t:10.4f} {pct:5.1f}%")


if __name__ == "__main__":
    main()
