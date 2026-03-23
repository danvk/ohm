"""Calculate square kilometers covered by admin_level=2 and admin_level=4 boundaries per decade.

Reads a planet.osm.pbf file, finds all relations/ways tagged with
boundary=administrative and admin_level=2 or admin_level=4, parses their
start_date/end_date tags, and outputs a table of (decade year, km², km²) for
every year ending in zero.
"""

import argparse
import functools
import heapq
import json
import sys
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

import osmium
import osmium.geom
import pyproj
from shapely.geometry import shape
from shapely.ops import transform as shapely_transform
from shapely.ops import unary_union

# Transformer from WGS84 lon/lat → equal-area projection (EPSG:6933) for km²
_transformer = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:6933", always_xy=True)
_to_equal_area = functools.partial(_transformer.transform)


def area_km2(geom) -> float:
    """Return the area of a Shapely geometry in square kilometres."""
    projected = shapely_transform(_to_equal_area, geom)
    return projected.area / 1e6


def parse_year(date_str: str) -> int | None:
    """Extract the year from a YYYY or YYYY-MM-DD string (supports negatives)."""
    if not date_str:
        return None
    s = date_str.strip()
    # Handle negative years: "-0500" or "-0500-01-01"
    try:
        year_part = (
            s.split("-")[0] if not s.startswith("-") else "-" + s[1:].split("-")[0]
        )
        return int(year_part)
    except (ValueError, IndexError):
        return None


def decade_years(start: int | None, end: int | None) -> list[int]:
    """Return all decade years (multiples of 10) in the range [start, end]."""
    # Open-ended: if no start_date assume it extends back to antiquity; if no
    # end_date assume it is still current (use year 2030 as a sentinel so we
    # include 2020 and 2030).
    lo = start if start is not None else -6000
    hi = end if end is not None else 2030
    if lo > hi:
        return []
    # Handle negative modulo correctly (Python's // floors toward -inf)
    first_decade = (lo // 10) * 10
    if first_decade < lo:
        first_decade += 10
    return list(range(first_decade, hi + 1, 10))


ADMIN_LEVELS = ("2", "4")


class DecadeCoverageHandler(osmium.SimpleHandler):
    def __init__(self):
        super().__init__()
        self.geojson = osmium.geom.GeoJSONFactory()
        # admin_level → decade_year → list of Shapely geometries valid in that year
        self.decade_geoms: dict[str, dict[int, list]] = {
            lvl: defaultdict(list) for lvl in ADMIN_LEVELS
        }
        self._captured_ids: set[tuple[str, int]] = set()
        self.totals: dict[str, int] = {lvl: 0 for lvl in ADMIN_LEVELS}
        self.skipped_no_date = 0
        # Track the earliest features per level: list of (start_year, label)
        self.earliest: dict[str, list[tuple[int, str]]] = {
            lvl: [] for lvl in ADMIN_LEVELS
        }

    def _admin_level(self, tags) -> str | None:
        """Return the admin_level if this is a relevant boundary, else None."""
        if tags.get("boundary") != "administrative":
            return None
        lvl = tags.get("admin_level")
        return lvl if lvl in ADMIN_LEVELS else None

    def area(self, a: Any) -> None:
        admin_level = self._admin_level(a.tags)
        if admin_level is None:
            return

        orig_type = "way" if a.from_way() else "relation"
        orig_id = a.orig_id()
        key = (orig_type, orig_id)
        if key in self._captured_ids:
            return
        self._captured_ids.add(key)

        try:
            geometry_str = self.geojson.create_multipolygon(a)
        except Exception:
            return

        start_year = parse_year(a.tags.get("start_date", ""))
        end_year = parse_year(a.tags.get("end_date", ""))

        # Skip features with no date information at all.
        if start_year is None and end_year is None:
            self.skipped_no_date += 1
            return

        if start_year is None and end_year in (1871, 1872):
            # Patch for, e.g., relation/2687358
            start_year = 600

        years = decade_years(start_year, end_year)
        if not years:
            self.skipped_no_date += 1
            return

        geom = shape(json.loads(geometry_str))
        if not geom.is_valid:
            geom = geom.buffer(0)

        for y in years:
            self.decade_geoms[admin_level][y].append(geom)

        name = a.tags.get("name") or f"{orig_type}/{orig_id}"
        min_year = years[0]
        if min_year == -6000:
            sys.stderr.write(
                f"-6000: {orig_type}/{orig_id} at {admin_level=} {area_km2(geom):g} km^2 {name}\n"
            )

        # Record for earliest-feature reporting
        heap = self.earliest[admin_level]
        if len(heap) < 10:
            heapq.heappush(heap, (-min_year, name))
        elif min_year < -heap[0][0]:
            heapq.heapreplace(heap, (-min_year, name))

        self.totals[admin_level] += 1
        total = sum(self.totals.values())
        if total % 100 == 0:
            counts = ", ".join(
                f"L{level}={self.totals[level]}" for level in ADMIN_LEVELS
            )
            print(f"  {total} features processed ({counts})...", file=sys.stderr)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Calculate km² covered by admin_level=2 boundaries for each decade year."
        )
    )
    parser.add_argument("osm_file", help="Path to the .osm.pbf file")
    args = parser.parse_args()

    print(f"Reading {args.osm_file} ...", file=sys.stderr)
    handler = DecadeCoverageHandler()

    try:
        handler.apply_file(args.osm_file, locations=True)
    except RuntimeError as e:
        print(f"Error reading file: {e}", file=sys.stderr)
        sys.exit(1)

    total = sum(handler.totals.values())
    counts = ", ".join(
        f"admin_level={level}: {handler.totals[level]}" for level in ADMIN_LEVELS
    )
    print(
        f"Read {total} features ({counts}); "
        f"{handler.skipped_no_date} skipped — no decade year in range.",
        file=sys.stderr,
    )
    print("Computing unions and areas...", file=sys.stderr)

    # Collect all decade years across both levels
    all_decades = sorted(
        set().union(*[d.keys() for d in handler.decade_geoms.values()])
    )

    # Report earliest 10 features per level (heap stores (-start_year, name))
    for lvl in ADMIN_LEVELS:
        top10 = sorted(
            handler.earliest[lvl]
        )  # ascending by -start_year → most-negative first
        print(f"  Earliest admin_level={lvl} features:", file=sys.stderr)
        for neg_yr, name in top10:
            print(f"    {-neg_yr}: {name}", file=sys.stderr)

    # Compute union area for one (level, decade) bucket.
    def compute_bucket(lvl: str, decade: int, geoms: list) -> tuple[int, str, float]:
        """Returns (decade, lvl, km2) using unary_union."""
        if not geoms:
            return decade, lvl, 0.0
        union = unary_union(geoms)
        return decade, lvl, area_km2(union)

    # Results: decade → {lvl: km2}
    results: dict[int, dict[str, float]] = {d: {} for d in all_decades}

    for lvl in ADMIN_LEVELS:
        lvl_geoms = handler.decade_geoms[lvl]
        buckets = [(decade, lvl_geoms.get(decade, [])) for decade in all_decades]
        n_buckets = sum(1 for _, g in buckets if g)

        print(
            f"  admin_level={lvl}: computing {n_buckets} decade buckets...",
            file=sys.stderr,
        )
        t0 = time.monotonic()
        done = 0

        with ThreadPoolExecutor(max_workers=3) as pool:
            futures = {
                pool.submit(compute_bucket, lvl, decade, geoms): decade
                for decade, geoms in buckets
            }
            for future in as_completed(futures):
                decade, lvl, km2 = future.result()
                results[decade][lvl] = km2
                done += 1
                if done % 50 == 0 or done == n_buckets:
                    elapsed = time.monotonic() - t0
                    print(
                        f"    L{lvl}: {done}/{n_buckets} buckets done in {elapsed:.0f}s",
                        file=sys.stderr,
                    )

        elapsed = time.monotonic() - t0
        print(f"  admin_level={lvl} done in {elapsed:.0f}s.", file=sys.stderr)

    # Print tab-delimited table
    print("\t".join(["year"] + [f"admin{level}_km2" for level in ADMIN_LEVELS]))
    for decade in all_decades:
        vals = "\t".join(f"{results[decade].get(lvl, 0.0):.0f}" for lvl in ADMIN_LEVELS)
        print(f"{decade}\t{vals}")


if __name__ == "__main__":
    main()
