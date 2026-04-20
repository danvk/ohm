#!/usr/bin/env python3
"""Compute WHM and OHM earth-year coverage broken down by region × era.

Regions come from whm/world.geojson (17 regions).
Eras come from whm/eras.txt (10 eras, start_year,end_year per line).

For each (region, era) pair, sums the earth-years covered by each dataset.
Output CSV has columns: Region,Era,WHM,OHM

Usage:
    uv run region_era_coverage.py -o /tmp/region_era.csv
"""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from pathlib import Path

import shapely
from shapely.geometry import shape
from shapely.ops import unary_union
from shapely.strtree import STRtree
from tqdm import tqdm

from dates import to_fractional_year
from earth_coverage import EARTH_LAND_AREA_KM2, area_km2
from whm_gap import load_features, Feature

# ── Era / region helpers ──────────────────────────────────────────────────────


@dataclass
class Era:
    label: str  # e.g. "-3000 to -1500"
    start: float  # fractional year
    end: float  # fractional year


def load_eras(path: Path) -> list[Era]:
    eras: list[Era] = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            start_s, end_s = line.split(",")
            start_y, end_y = int(start_s), int(end_s)
            eras.append(
                Era(
                    label=f"{start_y} to {end_y}",
                    start=float(start_y),
                    end=float(end_y),
                )
            )
    return eras


@dataclass
class Region:
    name: str
    geom: object  # Shapely geometry


def load_regions(path: Path) -> list[Region]:
    with open(path) as f:
        gj = json.load(f)
    regions = []
    for feat in gj["features"]:
        geom = shape(feat["geometry"])
        if not geom.is_valid:
            geom = geom.buffer(0)
        regions.append(Region(name=feat["properties"]["name"], geom=geom))
    return regions


# ── Accumulator ───────────────────────────────────────────────────────────────


def accumulate(
    features: list[Feature],
    regions: list[Region],
    eras: list[Era],
    region_tree: STRtree,
) -> dict[tuple[str, str], float]:
    """Return {(region_name, era_label): earth_years} for a list of features."""
    totals: dict[tuple[str, str], float] = {}

    for feat in tqdm(features, unit="feat", smoothing=0):
        feat_start = to_fractional_year(feat.start)
        feat_end = to_fractional_year(feat.end)
        if feat_end <= feat_start:
            continue

        # Which regions does this feature touch?
        candidate_idxs = region_tree.query(feat.geom, predicate="intersects")
        if len(candidate_idxs) == 0:
            continue

        for ridx in candidate_idxs:
            region = regions[ridx]
            try:
                clipped_geom = feat.geom.intersection(region.geom)
            except Exception:
                try:
                    clipped_geom = shapely.make_valid(feat.geom).intersection(
                        shapely.make_valid(region.geom)
                    )
                except Exception:
                    continue

            if clipped_geom.is_empty:
                continue

            clipped_km2 = area_km2(clipped_geom)
            if clipped_km2 <= 0:
                continue

            for era in eras:
                t_start = max(feat_start, era.start)
                t_end = min(feat_end, era.end)
                if t_end <= t_start:
                    continue
                duration = t_end - t_start
                ey = clipped_km2 * duration / EARTH_LAND_AREA_KM2
                key = (region.name, era.label)
                totals[key] = totals.get(key, 0.0) + ey

    return totals


# ── Main ──────────────────────────────────────────────────────────────────────


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Compute WHM and OHM earth-year coverage by region × era."
    )
    ap.add_argument(
        "--ohm-dir",
        type=Path,
        default=Path("/Users/danvk/code/ohmdash/boundary"),
    )
    ap.add_argument(
        "--whm-dir",
        type=Path,
        default=Path("/Users/danvk/code/ohmdash/whm-boundary"),
    )
    ap.add_argument(
        "--world",
        type=Path,
        default=Path(__file__).parent / "whm/world.geojson",
    )
    ap.add_argument(
        "--eras",
        type=Path,
        default=Path(__file__).parent / "whm/eras.txt",
    )
    ap.add_argument("-o", "--output", type=Path, default=Path("/tmp/region_era.csv"))
    args = ap.parse_args()

    eras = load_eras(args.eras)
    print(f"Loaded {len(eras)} eras")

    regions = load_regions(args.world)
    print(f"Loaded {len(regions)} regions")
    region_tree = STRtree([r.geom for r in regions])

    ohm_features = load_features(
        args.ohm_dir / "relations2.json",
        args.ohm_dir / "ways2.json",
        desc="OHM",
    )
    whm_features = load_features(
        args.whm_dir / "relations2.json",
        args.whm_dir / "ways2.json",
        desc="WHM",
    )

    print("\nAccumulating WHM …")
    whm_totals = accumulate(whm_features, regions, eras, region_tree)

    print("\nAccumulating OHM …")
    ohm_totals = accumulate(ohm_features, regions, eras, region_tree)

    # Collect all (region, era) keys that appear in either dataset
    all_keys = set(whm_totals) | set(ohm_totals)

    # Write CSV in region-major, era-minor order
    region_order = [r.name for r in regions]
    era_order = [e.label for e in eras]

    rows = []
    for rname in region_order:
        for elabel in era_order:
            key = (rname, elabel)
            whm_ey = whm_totals.get(key, 0.0)
            ohm_ey = ohm_totals.get(key, 0.0)
            if whm_ey > 0 or ohm_ey > 0:
                rows.append(
                    {
                        "Region": rname,
                        "Era": elabel,
                        "WHM": f"{whm_ey:.6f}",
                        "OHM": f"{ohm_ey:.6f}",
                    }
                )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["Region", "Era", "WHM", "OHM"])
        w.writeheader()
        w.writerows(rows)

    print(f"\nWrote {len(rows)} rows → {args.output}")

    # Quick summary: top gaps
    print("\nTop 20 (region, era) gaps (WHM - OHM):")
    print(f"  {'region':<35} {'era':<20} {'WHM':>8} {'OHM':>8} {'gap':>8}")
    print("  " + "-" * 82)
    gap_rows = sorted(
        rows, key=lambda r: float(r["WHM"]) - float(r["OHM"]), reverse=True
    )
    for r in gap_rows[:20]:
        gap = float(r["WHM"]) - float(r["OHM"])
        print(
            f"  {r['Region']:<35} {r['Era']:<20} {float(r['WHM']):8.4f} {float(r['OHM']):8.4f} {gap:8.4f}"
        )


if __name__ == "__main__":
    main()
