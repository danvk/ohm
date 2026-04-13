"""Calculate "Earth Years" covered by admin_level features.

Reads a planet.osm.pbf file, finds all relations/ways tagged with
boundary=administrative and admin_level=2 or admin_level=4, parses their
start_date/end_date tags.
"""

import argparse
import heapq
import re
import sys
from collections import defaultdict
from dataclasses import dataclass

import numpy as np
import osmium
import osmium.filter
import osmium.geom
import osmium.io
import pyproj
import shapely
from osmium.osm.types import Area
from shapely.geometry.base import BaseGeometry
from shapely.strtree import STRtree
from tqdm import tqdm

from dates import Range, duration_years, parse_ohm_date, start_of_date
from stats import log_start, write_stats

EARTH_LAND_AREA_KM2 = 149_000_000


@dataclass
class OverlapFeature:
    ftype: str  # 'r' or 'w'
    fid: int
    name: str
    geom: BaseGeometry
    date_range: Range  # (start_DateTuple, end_DateTuple)
    area_km2: float


# Transformer from WGS84 lon/lat → equal-area projection (EPSG:6933) for km²
_transformer = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:6933", always_xy=True)


def _transform_coords(coords):
    """Transform an (N, 2) lon/lat array to equal-area x/y in one vectorized call."""
    x, y = _transformer.transform(coords[:, 0], coords[:, 1])
    return np.column_stack([x, y])


def area_km2(geom) -> float:
    """Return the area of a Shapely geometry in square kilometres.

    Uses shapely.transform (Shapely 2.x) which passes all coordinates as a
    numpy array in one call, avoiding the per-coordinate Python overhead of
    the older shapely.ops.transform approach.
    """
    projected = shapely.transform(geom, _transform_coords, include_z=False)
    return projected.area / 1e6


ADMIN_LEVELS = ("1", "2", "3", "4")


class CoverageHandler(osmium.SimpleHandler):
    def __init__(self, planet_timestamp: str):
        super().__init__()
        self.wkb = osmium.geom.WKBFactory()
        self.skipped_no_date = 0
        self.skipped_no_start = 0
        self.planet_date = parse_ohm_date(planet_timestamp[:10])
        self.totals = defaultdict[str, float](float)
        # raw_examples[admin_level] = [(earth_years, ftype, fid, description)]
        self.raw_examples: dict[str, list[tuple[float, str, int, str]]] = defaultdict(
            list
        )
        self.n_features = 0
        self.n_nonclosed = 0
        # features[admin_level] = list of OverlapFeature (for overlap computation)
        self.features: dict[str, list[OverlapFeature]] = defaultdict(list)

    def _admin_level(self, tags) -> str | None:
        """Return the admin_level if this is a relevant boundary, else None."""
        if tags.get("boundary") != "administrative":
            return None
        lvl = tags.get("admin_level")
        return lvl if lvl in ADMIN_LEVELS else None

    def area(self, a: Area) -> None:
        admin_level = self._admin_level(a.tags)
        if admin_level is None:
            return

        start_date = parse_ohm_date(a.tags.get("start_date"))
        end_date = parse_ohm_date(a.tags.get("end_date"))

        # Skip features with no date information at all.
        # These should be filtered out before getting here.
        if start_date is None and end_date is None:
            self.skipped_no_date += 1
            return

        if start_date is None:
            self.skipped_no_start += 1
            return

        if not end_date:
            end_date = self.planet_date

        assert start_date is not None and end_date is not None
        date_range = (start_of_date(start_date), start_of_date(end_date))
        duration_y = duration_years(date_range)

        orig_type = "w" if a.from_way() else "r"
        orig_id = a.orig_id()
        try:
            wkb = self.wkb.create_multipolygon(a)
        except Exception:
            return

        geom = shapely.from_wkb(wkb)
        if not geom.is_valid:
            geom = geom.buffer(0)

        geom_km2 = area_km2(geom)
        area_y_km2 = duration_y * geom_km2
        earth_yrs = area_y_km2 / EARTH_LAND_AREA_KM2
        self.totals[admin_level] += area_y_km2

        name = a.tags.get("name:en") or a.tags.get("name") or ""
        self.features[admin_level].append(
            OverlapFeature(
                ftype=orig_type,
                fid=orig_id,
                name=name,
                geom=geom,
                date_range=date_range,
                area_km2=geom_km2,
            )
        )
        start_tag = a.tags.get("start_date", "?")
        end_tag = a.tags.get("end_date", "present")
        desc = f"{earth_yrs:.4f} earth-yr; {name} ({start_tag}–{end_tag})"
        self.raw_examples[admin_level].append((earth_yrs, orig_type, orig_id, desc))

        self.n_features += 1
        if self.n_features % 100 == 0:
            counts = ", ".join(
                f"L{level}={self.totals[level]}" for level in ADMIN_LEVELS
            )
            print(
                f"  {self.n_features} features processed ({counts})...", file=sys.stderr
            )


def compute_pairwise_overlaps(
    features: list[OverlapFeature],
    level: str,
    min_earth_years: float = 0.0,
) -> tuple[float, list[tuple[float, str, int, str, int, str]]]:
    """Find all pairs of features that overlap in both space and time.

    Uses a temporal sweep line so that spatial intersection is only tested
    against features that are temporally active (overlapping in time).

    Returns (total_earth_years, sorted_results) where each result is
    (earth_yrs, ftype_a, fid_a, ftype_b, fid_b, desc).
    """
    if len(features) < 2:
        return 0.0, []

    # Sort by start_date so we can sweep and expire features as time advances.
    order = sorted(range(len(features)), key=lambda k: features[k].date_range[0])
    sorted_feats = [features[k] for k in order]

    # Simplified geometries for fast spatial rejection (STRtree uses these).
    simplified = [f.geom.simplify(0.1, preserve_topology=False) for f in sorted_feats]
    tree = STRtree(simplified)

    total = 0.0
    results: list[tuple[float, str, int, str, int, str]] = []

    # active_set: sorted indices that have started and not yet expired.
    # expiry_heap: min-heap of (end_date, sorted_index) for efficient expiry.
    active_set: set[int] = set()
    expiry_heap: list[tuple[tuple[int, int, int], int]] = []

    for k, feat_k in enumerate(
        tqdm(sorted_feats, desc=f"admin_level={level}", unit="feat", smoothing=0)
    ):
        start_k, end_k = feat_k.date_range

        # Expire features that ended at or before start_k (no temporal overlap).
        while expiry_heap and expiry_heap[0][0] <= start_k:
            _, expired = heapq.heappop(expiry_heap)
            active_set.discard(expired)

        # Query STRtree for spatially-nearby candidates (bbox + simplified intersects).
        candidates = tree.query(simplified[k], predicate="intersects")

        for j in candidates:
            # Only check against already-active features (j < k in sorted order).
            # This guarantees temporal overlap and avoids processing each pair twice.
            if j not in active_set:
                continue

            feat_j = sorted_feats[j]

            # Upper-bound check: intersection can't exceed the smaller feature's area.
            overlap_start = max(start_k, feat_j.date_range[0])
            overlap_end = min(end_k, feat_j.date_range[1])
            overlap_range: Range = (overlap_start, overlap_end)
            dur_y = duration_years(overlap_range)
            max_earth_yrs = (
                dur_y * min(feat_k.area_km2, feat_j.area_km2) / EARTH_LAND_AREA_KM2
            )
            if max_earth_yrs < min_earth_years:
                continue

            # Full geometric intersection.
            intersection = feat_k.geom.intersection(feat_j.geom)
            if intersection.is_empty:
                continue

            km2 = area_km2(intersection)
            earth_yrs = dur_y * km2 / EARTH_LAND_AREA_KM2

            desc = (
                f"{earth_yrs:.4f} earth-yr; "
                f"{feat_k.ftype}/{feat_k.fid} × {feat_j.ftype}/{feat_j.fid} "
                f"{feat_k.name}|{feat_j.name} "
                f"({overlap_start[0]}–{overlap_end[0]})"
            )
            results.append(
                (earth_yrs, feat_k.ftype, feat_k.fid, feat_j.ftype, feat_j.fid, desc)
            )
            total += earth_yrs

        # Add k to the active set after checking (so it's available for future features).
        active_set.add(k)
        heapq.heappush(expiry_heap, (end_k, k))

    results.sort(key=lambda x: x[0], reverse=True)
    return total, results


def main() -> None:
    parser = argparse.ArgumentParser(
        description=("Calculate OHM coverage of admin_level features in earth years.")
    )
    parser.add_argument("osm_file", help="Path to the .osm.pbf file")
    parser.add_argument("--output_dir", default=".")
    parser.add_argument(
        "--min_overlap_earth_years",
        type=float,
        default=0.01,
        help="Skip pairs whose upper-bound overlap is below this threshold (default: 0.01)",
    )
    args = parser.parse_args()

    log_start("earth-coverage")
    print(f"Reading {args.osm_file} ...", file=sys.stderr)

    with osmium.io.Reader(args.osm_file) as r:
        h = r.header()
        timestamp = h.get("timestamp")

    if not timestamp:
        # try to get it from the file name, e.g. planet-250701_0002.osm.pbf
        m = re.search(r"planet-(\d\d)(\d\d)(\d\d)", args.osm_file)
        if m:
            (yy, mm, dd) = m.groups()
            timestamp = f"20{yy}-{mm}-{dd}"

    assert timestamp, "Unable to get timestamp from PBF header or file name."
    print(f"{timestamp=}", file=sys.stderr)

    handler = CoverageHandler(timestamp)
    handler.apply_file(
        args.osm_file,
        filters=[
            osmium.filter.KeyFilter("admin_level"),
            osmium.filter.KeyFilter("start_date", "end_date"),
        ],
    )

    sys.stderr.write(
        f"Read {handler.n_features} features ; "
        f"{handler.skipped_no_date=} {handler.skipped_no_start=} {handler.n_nonclosed=}.\n",
    )
    counts = {
        f"earth-years-admin-{level}": round(area_y_km2 / EARTH_LAND_AREA_KM2, 6)
        for level, area_y_km2 in handler.totals.items()
    }

    examples: dict[str, list[tuple[str, int, str]]] = {}
    for level, items in handler.raw_examples.items():
        items.sort(key=lambda x: x[0], reverse=True)
        examples[f"earth-years-admin-{level}"] = [
            (ftype, fid, desc) for _, ftype, fid, desc in items
        ]

    write_stats(
        args.output_dir,
        "earth-coverage",
        examples,
        counts,
        preserve_sort_order=True,
    )

    # Compute pairwise overlaps per admin level sequentially to limit RAM usage.
    log_start("earth-coverage-overlap")
    print("Computing pairwise overlaps...", file=sys.stderr)
    overlap_counts: dict[str, float] = {}
    overlap_examples: dict[str, list[tuple[str, int, str]]] = {}

    for level in ADMIN_LEVELS:
        feats = handler.features.get(level, [])
        if len(feats) < 2:
            continue
        total_ey, pairs = compute_pairwise_overlaps(
            feats, level, args.min_overlap_earth_years
        )
        key = f"double-covered-admin-{level}"
        overlap_counts[key] = round(total_ey, 6)
        overlap_examples[key] = [
            (ftype_a, fid_a, desc) for _, ftype_a, fid_a, *_, desc in pairs
        ]
        print(
            f"  admin_level={level}: {len(pairs)} overlapping pairs, "
            f"{total_ey:.4f} double-covered earth-years",
            file=sys.stderr,
        )

    write_stats(
        args.output_dir,
        "earth-coverage-overlap",
        overlap_examples,
        overlap_counts,
        preserve_sort_order=True,
    )


if __name__ == "__main__":
    main()
