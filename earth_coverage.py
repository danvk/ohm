"""Calculate "Earth Years" covered by admin_level features.

Reads a planet.osm.pbf file, finds all relations/ways tagged with
boundary=administrative and admin_level=2 or admin_level=4, parses their
start_date/end_date tags.
"""

import argparse
import functools
import json
import sys
from collections import defaultdict

import osmium
import osmium.filter
import osmium.geom
import pyproj
from osmium.osm.types import Area
from shapely.geometry import shape
from shapely.ops import transform as shapely_transform

from dates import DateTuple, duration_years, parse_ohm_date, start_of_date

EARTH_LAND_AREA_KM2 = 149_000_000

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


class CoverageHandler(osmium.SimpleHandler):
    def __init__(self):
        super().__init__()
        self.geojson = osmium.geom.GeoJSONFactory()
        self.skipped_no_date = 0
        self.skipped_no_start = 0
        self.planet_date: DateTuple = (2026, 3, 1)  # todo: derive from timestamp
        self.totals = defaultdict[str, float](float)
        self.n_features = 0

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

        duration_y = duration_years(
            (start_of_date(start_date), start_of_date(end_date))
        )

        # orig_type = "way" if a.from_way() else "relation"
        # orig_id = a.orig_id()
        try:
            geometry_str = self.geojson.create_multipolygon(a)
        except Exception:
            return

        geom = shape(json.loads(geometry_str))
        if not geom.is_valid:
            geom = geom.buffer(0)

        self.totals[admin_level] += duration_y * area_km2(geom)
        self.n_features += 1
        if self.n_features % 100 == 0:
            counts = ", ".join(
                f"L{level}={self.totals[level]}" for level in ADMIN_LEVELS
            )
            print(
                f"  {self.n_features} features processed ({counts})...", file=sys.stderr
            )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=("Calculate OHM coverage of admin_level features in earth years.")
    )
    parser.add_argument("osm_file", help="Path to the .osm.pbf file")
    args = parser.parse_args()

    print(f"Reading {args.osm_file} ...", file=sys.stderr)
    handler = CoverageHandler()

    handler.apply_file(
        args.osm_file,
        filters=[
            osmium.filter.KeyFilter("admin_level"),
            osmium.filter.KeyFilter("start_date", "end_date"),
        ],
    )

    counts = "\n".join(
        f"admin_level={level}: {handler.totals[level] / EARTH_LAND_AREA_KM2}"
        for level in ADMIN_LEVELS
    )
    print(
        f"Read {handler.n_features} features ({counts}); "
        f"{handler.skipped_no_date=} {handler.skipped_no_start=}.",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
