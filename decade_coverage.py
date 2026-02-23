"""Calculate square kilometers covered by admin_level=2 boundaries per decade.

Reads a planet.osm.pbf file, finds all relations/ways tagged with
boundary=administrative and admin_level=2, parses their start_date/end_date
tags, and outputs a table of (decade year, km²) for every year ending in zero.
"""

import argparse
import functools
import json
import sys
from collections import defaultdict
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


class DecadeCoverageHandler(osmium.SimpleHandler):
    def __init__(self):
        super().__init__()
        self.geojson = osmium.geom.GeoJSONFactory()
        # decade_year → list of Shapely geometries valid in that year
        self.decade_geoms: dict[int, list] = defaultdict(list)
        self._captured_ids: set[tuple[str, int]] = set()
        self.total = 0
        self.skipped_no_date = 0

    def _is_admin2(self, tags) -> bool:
        return (
            tags.get("boundary") == "administrative" and tags.get("admin_level") == "2"
        )

    def area(self, a: Any) -> None:
        if not self._is_admin2(a.tags):
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

        years = decade_years(start_year, end_year)
        if not years:
            self.skipped_no_date += 1
            return

        geom = shape(json.loads(geometry_str))
        if not geom.is_valid:
            geom = geom.buffer(0)

        if not start_year:
            area = area_km2(geom)
            sys.stderr.write(
                f"Missing start date for {orig_type}/{orig_id} area_km2={area}\n"
            )

        for y in years:
            self.decade_geoms[y].append(geom)

        self.total += 1
        if self.total % 100 == 0:
            print(f"  {self.total} features processed...", file=sys.stderr)


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

    print(
        f"Read {handler.total} features "
        f"({handler.skipped_no_date} skipped — no decade year in range).",
        file=sys.stderr,
    )
    print("Computing unions and areas...", file=sys.stderr)

    rows: list[tuple[int, float]] = []
    for decade in sorted(handler.decade_geoms):
        geoms = handler.decade_geoms[decade]
        union = unary_union(geoms)
        km2 = area_km2(union)
        rows.append((decade, km2))

    # Print table
    print("Year\tkm²")
    for year, km2 in rows:
        print(f"{year}\t{km2}")


if __name__ == "__main__":
    main()
