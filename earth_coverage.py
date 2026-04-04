"""Calculate "Earth Years" covered by admin_level features.

Reads a planet.osm.pbf file, finds all relations/ways tagged with
boundary=administrative and admin_level=2 or admin_level=4, parses their
start_date/end_date tags.
"""

import argparse
import functools
import json
import re
import sys
from collections import defaultdict

import osmium
import osmium.filter
import osmium.geom
import osmium.io
import pyproj
from osmium.osm.types import Area
from shapely.geometry import shape
from shapely.ops import transform as shapely_transform

from dates import duration_years, parse_ohm_date, start_of_date
from stats import write_stats

EARTH_LAND_AREA_KM2 = 149_000_000

# Transformer from WGS84 lon/lat → equal-area projection (EPSG:6933) for km²
_transformer = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:6933", always_xy=True)
_to_equal_area = functools.partial(_transformer.transform)


def area_km2(geom) -> float:
    """Return the area of a Shapely geometry in square kilometres."""
    projected = shapely_transform(_to_equal_area, geom)
    return projected.area / 1e6


ADMIN_LEVELS = ("1", "2", "3", "4")


class CoverageHandler(osmium.SimpleHandler):
    def __init__(self, planet_timestamp: str):
        super().__init__()
        self.geojson = osmium.geom.GeoJSONFactory()
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

        orig_type = "w" if a.from_way() else "r"
        orig_id = a.orig_id()
        try:
            geometry_str = self.geojson.create_multipolygon(a)
        except Exception:
            return

        geom = shape(json.loads(geometry_str))
        if not geom.is_valid:
            geom = geom.buffer(0)

        area_y_km2 = duration_y * area_km2(geom)
        earth_yrs = area_y_km2 / EARTH_LAND_AREA_KM2
        self.totals[admin_level] += area_y_km2

        name = a.tags.get("name", "")
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


def main() -> None:
    parser = argparse.ArgumentParser(
        description=("Calculate OHM coverage of admin_level features in earth years.")
    )
    parser.add_argument("osm_file", help="Path to the .osm.pbf file")
    parser.add_argument("--output_dir", default=".")
    args = parser.parse_args()

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
        examples[f"admin-{level}"] = [
            (ftype, fid, desc) for _, ftype, fid, desc in items
        ]

    write_stats(
        args.output_dir,
        "earth-coverage",
        examples,
        counts,
        preserve_sort_order=True,
    )


if __name__ == "__main__":
    main()
