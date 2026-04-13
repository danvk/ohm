#!/usr/bin/env python3
"""
Unproject WHM SVG political borders to GeoJSON.

The WHM (World History Maps) SVGs use a hybrid pseudo-cylindrical projection:

    Latitude  (y-direction): equirectangular
        lat = 90 - y / Y_SCALE          (Y_SCALE = 180 units/degree)

    Longitude (x-direction): Robinson-style horizontal compression
        lon = LON0 + (x - X_OFFSET) / (X_SCALE * PLEN(lat))

where PLEN(lat) is the Robinson table latitude-dependent scale factor, and:
    Y_SCALE  = 180        (SVG viewBox height 32400 / 180° latitude)
    X_SCALE  = 8564.3     (Robinson x-scale; equals ~150 units/° at equator)
    X_OFFSET = 27585      (SVG x at central meridian / equator)
    LON0     = 15.0°      (central meridian, central European time meridian)

Calibrated from 10+ small-territory SVG text labels (Malta, Singapore,
Gibraltar, Barbados, Bahrain, Kuwait, Djibouti, El Salvador, Iceland, Trinidad)
using least-squares fit of the Robinson x-compression model.
Residuals: mean ≈ 0.31° longitude, ≈ 0.45° latitude.

Usage:
    python whm/unproject.py whm/WA2014.svg            # writes whm/WA2014.geojson
    python whm/unproject.py whm/WA2014.svg -o out.geojson
    python whm/unproject.py whm/WA2014.svg --layer ctry
"""
import re
import json
import math
import argparse
from pathlib import Path
from xml.etree import ElementTree as ET

# ── Projection parameters ──────────────────────────────────────────────────────
Y_SCALE: float  = 180.0    # SVG units per degree latitude (equirectangular)
X_SCALE: float  = 8564.3   # Robinson x-scale factor (SVG units per radian)
X_OFFSET: float = 27585.0  # SVG x at central meridian (equator)
LON0: float     = 15.0     # Central meridian longitude (degrees)

# Robinson projection horizontal scale factors (PLEN) at 5° latitude intervals.
# Source: Robinson (1974). Interpolated linearly between tabulated values.
# PLEN[i] corresponds to abs(lat) = i * 5 degrees.
_ROBINSON_PLEN = [
    1.0000, 0.9986, 0.9954, 0.9900,   #  0,  5, 10, 15
    0.9822, 0.9730, 0.9600, 0.9427,   # 20, 25, 30, 35
    0.9216, 0.8962, 0.8679, 0.8350,   # 40, 45, 50, 55
    0.7986, 0.7597, 0.7186, 0.6732,   # 60, 65, 70, 75
    0.6213, 0.5722, 0.5322,           # 80, 85, 90
]


def _plen(lat_abs: float) -> float:
    """Interpolate Robinson PLEN factor for |latitude| in degrees."""
    idx = lat_abs / 5.0
    i = int(idx)
    f = idx - i
    if i >= len(_ROBINSON_PLEN) - 1:
        return _ROBINSON_PLEN[-1]
    return _ROBINSON_PLEN[i] * (1.0 - f) + _ROBINSON_PLEN[i + 1] * f


# ── Coordinate transform ───────────────────────────────────────────────────────

def svg_to_lonlat(x: float, y: float) -> tuple[float, float]:
    """Convert SVG (x, y) to geographic (longitude, latitude) in degrees."""
    lat = 90.0 - y / Y_SCALE
    p = _plen(abs(lat))
    lon = LON0 + (x - X_OFFSET) / (X_SCALE * math.pi / 180.0 * p)
    lon = ((lon + 180.0) % 360.0) - 180.0
    return lon, lat


# ── SVG path parser ────────────────────────────────────────────────────────────

def _tokens(d: str):
    """Yield tokens from an SVG path data string."""
    return re.findall(r'[MmLlSsZz]|[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?', d)


def parse_svg_path(d: str) -> list[list[tuple[float, float]]]:
    """
    Parse SVG path data into a list of closed rings.

    Supported commands:
      M / m  – absolute / relative moveto  (+ implicit L/l for extra pairs)
      L / l  – absolute / relative lineto
      S / s  – smooth cubic bezier (endpoint only; control points discarded)
      Z / z  – close path

    Returns a list of rings; each ring is a list of (x, y) SVG-unit tuples.
    """
    toks = _tokens(d)
    rings: list[list[tuple[float, float]]] = []
    current: list[tuple[float, float]] = []
    cx = cy = 0.0
    cmd = "M"
    i = 0

    def read_pair() -> tuple[float, float]:
        nonlocal i
        a, b = float(toks[i]), float(toks[i + 1])
        i += 2
        return a, b

    while i < len(toks):
        tok = toks[i]
        if tok in "MmLlSsZz":
            cmd = tok
            i += 1
            if cmd in "Zz":
                if current:
                    rings.append(current)
                current = []
            continue

        # Coordinate pair(s) for the current command
        try:
            if cmd == "M":
                cx, cy = read_pair()
                current = [(cx, cy)]
                cmd = "L"          # subsequent pairs are implicit L
            elif cmd == "m":
                dx, dy = read_pair()
                cx += dx; cy += dy
                current = [(cx, cy)]
                cmd = "l"
            elif cmd == "L":
                cx, cy = read_pair()
                current.append((cx, cy))
            elif cmd == "l":
                dx, dy = read_pair()
                cx += dx; cy += dy
                current.append((cx, cy))
            elif cmd in "Ss":
                # S x2 y2 x y  – skip control point, use endpoint
                _x2, _y2 = read_pair()   # control point (discarded)
                ex, ey = read_pair()      # endpoint
                if cmd == "S":
                    cx, cy = ex, ey
                else:
                    cx += ex; cy += ey
                current.append((cx, cy))
            else:
                i += 1
        except (ValueError, IndexError):
            i += 1

    if current:
        rings.append(current)

    return rings


# ── GeoJSON helpers ────────────────────────────────────────────────────────────

def rings_to_geometry(rings: list[list[tuple[float, float]]]) -> dict | None:
    """Convert SVG rings to a GeoJSON Polygon or MultiPolygon geometry."""
    geo_rings: list[list[tuple[float, float]]] = []
    for ring in rings:
        coords = [svg_to_lonlat(x, y) for x, y in ring]
        if not coords:
            continue
        if coords[0] != coords[-1]:
            coords.append(coords[0])   # close the ring
        geo_rings.append(coords)

    if not geo_rings:
        return None
    if len(geo_rings) == 1:
        return {"type": "Polygon", "coordinates": geo_rings}
    return {"type": "MultiPolygon", "coordinates": [[r] for r in geo_rings]}


def parse_id(path_id: str) -> tuple[str, str]:
    """
    Split a path id like '30439186-egypt' into (osm_id, name).
    Handles plain names without a numeric prefix.
    """
    m = re.match(r'^(\d+)-(.+)$', path_id)
    if m:
        return m.group(1), m.group(2)
    return "", path_id


# ── Main conversion ────────────────────────────────────────────────────────────

SVG_NS = "http://www.w3.org/2000/svg"


def unproject_svg(svg_path: Path, output_path: Path, layer: str | None = None) -> None:
    """Parse an SVG file and write un-projected political borders as GeoJSON."""
    tree = ET.parse(svg_path)
    root = tree.getroot()

    # Strip namespace prefix from tag comparisons
    def tag(local: str) -> str:
        return f"{{{SVG_NS}}}{local}"

    features: list[dict] = []

    for group_id in ("terr", "ctry"):
        if layer and layer != group_id:
            continue

        # Find the group element regardless of namespace prefix
        group = root.find(f'.//{tag("g")}[@id="{group_id}"]')
        if group is None:
            group = root.find(f'.//*[@id="{group_id}"]')
        if group is None:
            print(f"  Warning: group '{group_id}' not found")
            continue

        paths = list(group.iter(tag("path")))
        print(f"  Layer '{group_id}': {len(paths)} path elements")

        for path_el in paths:
            pid = path_el.get("id", "")
            d = path_el.get("d", "")
            if not d:
                continue

            rings = parse_svg_path(d)
            geometry = rings_to_geometry(rings)
            if geometry is None:
                continue

            osm_id, name = parse_id(pid)
            features.append(
                {
                    "type": "Feature",
                    "geometry": geometry,
                    "properties": {
                        "id": pid,
                        "name": name,
                        "osm_id": osm_id,
                        "layer": group_id,
                    },
                }
            )

    geojson = {
        "type": "FeatureCollection",
        "features": features,
        "metadata": {
            "source": str(svg_path),
            "projection": "hybrid pseudo-cylindrical (equirectangular-y / Robinson-x)",
            "y_scale": Y_SCALE,
            "x_scale": X_SCALE,
            "x_offset": X_OFFSET,
            "lon0": LON0,
            "note": (
                "Y-direction is equirectangular (lat = 90 - y/180). "
                "X-direction uses Robinson PLEN table for latitude-dependent "
                "horizontal compression. Calibrated from small-territory label "
                "positions; residuals ≈ 0.3° longitude."
            ),
        },
    }

    output_path.write_text(json.dumps(geojson, indent=2))
    print(f"Wrote {len(features)} features → {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Unproject WHM SVG political borders to GeoJSON"
    )
    parser.add_argument(
        "svg",
        type=Path,
        nargs="?",
        default=Path("whm/WA2014.svg"),
        help="Input SVG file (default: whm/WA2014.svg)",
    )
    parser.add_argument(
        "-o", "--output", type=Path, default=None,
        help="Output GeoJSON file (default: <svg>.geojson)",
    )
    parser.add_argument(
        "--layer", choices=["terr", "ctry"], default=None,
        help="Only process one layer (default: both terr and ctry)",
    )
    args = parser.parse_args()

    out = args.output or args.svg.with_suffix(".geojson")
    unproject_svg(args.svg, out, args.layer)
