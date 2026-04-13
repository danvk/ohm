#!/usr/bin/env python3
"""
Unproject WHM SVG political borders to GeoJSON.

The WHM (World History Maps) SVGs use the Winkel Tripel projection,
centered at 11°E (Central European time meridian).

SVG dimensions for the new-format files: 54001 × 32400 px.
Old-format files (25201 × 15120) use the same projection scaled by 15/7.

Calibrated from small-territory SVG text labels (Malta, Singapore,
Gibraltar, Barbados, Bahrain, Kuwait, Djibouti, El Salvador, Iceland,
Trinidad and many more).
Residuals: mean ≈ 0.25° longitude, ≈ 0.20° latitude.

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

# ── Winkel Tripel projection (ported from historymaps/winkel.py) ───────────────

_halfpi = math.pi / 2
_epsilon = 1e-6


def _sinci(x: float) -> float:
    return x / math.sin(x) if x else 1.0


def _safe_acos(x: float) -> float:
    if x > 1.0:
        return 0.0
    elif x < -1.0:
        return math.pi
    return math.acos(x)


def _aitoff(lam: float, phi: float) -> tuple[float, float]:
    """Aitoff component of Winkel Tripel (lam, phi in radians)."""
    cosphi = math.cos(phi)
    lam2 = lam / 2.0
    s = _sinci(_safe_acos(cosphi * math.cos(lam2)))
    return (2.0 * cosphi * math.sin(lam2) * s, math.sin(phi) * s)


def _winkel_project(lam: float, phi: float) -> tuple[float, float]:
    ax, ay = _aitoff(lam, phi)
    return ((ax + lam / _halfpi) / 2.0, (ay + phi) / 2.0)


def _winkel_invert(x: float, y: float) -> tuple[float, float]:
    """Invert Winkel Tripel via Newton iteration. Returns (lam, phi) in radians."""
    lam, phi = float(x), float(y)
    for _ in range(25):
        cos_phi     = math.cos(phi)
        sin_phi     = math.sin(phi)
        sin_2phi    = math.sin(2.0 * phi)
        sin2phi     = sin_phi * sin_phi
        cos2phi     = cos_phi * cos_phi
        sinlam      = math.sin(lam)
        coslam2     = math.cos(lam / 2.0)
        sinlam2     = math.sin(lam / 2.0)
        sin2lam2    = sinlam2 * sinlam2
        C = 1.0 - cos2phi * coslam2 * coslam2
        if C:
            F = 1.0 / C
            E = _safe_acos(cos_phi * coslam2) * math.sqrt(F)
        else:
            F = E = 0.0
        fx = 0.5 * (2.0 * E * cos_phi * sinlam2 + lam / _halfpi) - x
        fy = 0.5 * (E * sin_phi + phi) - y
        dxdl = 0.5 * F * (cos2phi * sin2lam2 + E * cos_phi * coslam2 * sin2phi) + 0.5 / _halfpi
        dxdp = F * (sinlam * sin_2phi / 4.0 - E * sin_phi * sinlam2)
        dydl = 0.125 * F * (sin_2phi * sinlam2 - E * sin_phi * cos2phi * sinlam)
        dydp = 0.5 * F * (sin2phi * coslam2 + E * sin2lam2 * cos_phi) + 0.5
        denom = dxdp * dydl - dydp * dxdl
        dlam  = (fy * dxdp - fx * dydp) / denom
        dphi  = (fx * dydl - fy * dxdl) / denom
        lam -= dlam
        phi -= dphi
        if abs(dlam) <= _epsilon and abs(dphi) <= _epsilon:
            break
    return lam, phi


# SVG canvas bounds for WA2014.svg (54001 × 32400)
_SVG_MAXX = 54001.0
_SVG_MAXY = 32400.0
_CENTER_LON = 11.0  # degrees — Central European time meridian

# The Euratlas SVG equator sits 22 pixels south of the canvas midline.
# Calibrated from the straight 49°N US-Canada border (17 SVG control points)
# and confirmed by island-territory text-label positions (9 control points):
# applying this shift moves the 49°N border to 48.98–49.00° and reduces the
# mean label error from 0.273° to 0.246°.
_Y_CENTER_OFFSET = 22.0   # pixels; equator is at SVG y = _SVG_MAXY/2 + this

# Winkel Tripel normalisation constants
_maxunitx, _ = _winkel_project(math.pi, 0.0)           # ≈ (π+2)/2 ≈ 2.5708
_, _maxunity  = _winkel_project(0.0, math.pi / 2.0)    # = π/2 ≈ 1.5708


# ── Correction mesh ────────────────────────────────────────────────────────────
# A (delta_lon, delta_lat) correction grid built by comparing WHM projected
# borders to admin0 reference borders.  Applied as a post-projection refinement.

_MESH_PATH = Path(__file__).with_name('correction_mesh.json')

def _load_mesh(path: Path = _MESH_PATH) -> dict | None:
    """Load correction mesh from JSON; return None if file not found."""
    if not path.exists():
        return None
    data = json.loads(path.read_text())
    return data

_mesh = _load_mesh()


def _mesh_correction(lon: float, lat: float) -> tuple[float, float]:
    """
    Return (delta_lon, delta_lat) at (lon, lat) via bilinear interpolation
    of the correction mesh.  Returns (0, 0) outside the mesh coverage or if
    no mesh is loaded.
    """
    if _mesh is None:
        return 0.0, 0.0

    lon_min: int = _mesh['lon_min']
    lat_min: int = _mesh['lat_min']
    lon_max: int = _mesh['lon_max']
    lat_max: int = _mesh['lat_max']
    dlon_grid = _mesh['dlon']
    dlat_grid = _mesh['dlat']

    # Fractional indices
    fi = lon - lon_min
    fj = lat - lat_min

    i0 = int(math.floor(fi))
    j0 = int(math.floor(fj))
    i1, j1 = i0 + 1, j0 + 1

    # Clamp to grid bounds
    if i0 < 0 or j0 < 0 or i1 >= (lon_max - lon_min + 1) or j1 >= (lat_max - lat_min + 1):
        return 0.0, 0.0

    tx = fi - i0   # 0..1 interpolation weight in x
    ty = fj - j0   # 0..1 interpolation weight in y

    def interp(grid: list) -> float:
        return (
            grid[j0][i0] * (1 - tx) * (1 - ty)
            + grid[j0][i1] * tx       * (1 - ty)
            + grid[j1][i0] * (1 - tx) * ty
            + grid[j1][i1] * tx       * ty
        )

    return interp(dlon_grid), interp(dlat_grid)


# ── Coordinate transform ───────────────────────────────────────────────────────

def svg_to_lonlat(x: float, y: float) -> tuple[float, float]:
    """Convert SVG (x, y) to geographic (longitude, latitude) in degrees."""
    # Map pixel coords to Winkel Tripel unit space.
    # Y is shifted by _Y_CENTER_OFFSET to account for the equator being 22 px
    # south of the canvas midline in the Euratlas SVG.
    unitx = (2.0 * x / _SVG_MAXX - 1.0) * _maxunitx
    unity = (2.0 * (y - _Y_CENTER_OFFSET) / _SVG_MAXY - 1.0) * _maxunity
    lam, phi = _winkel_invert(unitx, unity)
    lat = -math.degrees(phi)        # y↓ in SVG → negate for lat
    lon = math.degrees(lam) + _CENTER_LON
    lon = ((lon + 180.0) % 360.0) - 180.0

    # Apply correction mesh
    dlon, dlat = _mesh_correction(lon, lat)
    lon = ((lon + dlon + 180.0) % 360.0) - 180.0
    lat = lat + dlat

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

def _unwrap_ring(coords: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """
    Unwrap longitude jumps > 180° so antimeridian-crossing rings stay contiguous.

    Consecutive points that jump more than 180° in longitude are assumed to have
    crossed the antimeridian; their longitude is shifted by ±360° to keep the
    ring geometrically coherent.  The resulting coordinates may lie outside the
    canonical [-180, 180] range, which is intentional — it preserves the correct
    polygon shape for renderers that handle it (e.g. geojson.io / Mapbox GL).
    """
    if len(coords) < 2:
        return coords
    result = [coords[0]]
    for lon, lat in coords[1:]:
        prev_lon = result[-1][0]
        while lon - prev_lon > 180.0:
            lon -= 360.0
        while lon - prev_lon < -180.0:
            lon += 360.0
        result.append((lon, lat))
    return result


def rings_to_geometry(rings: list[list[tuple[float, float]]]) -> dict | None:
    """Convert SVG rings to a GeoJSON Polygon or MultiPolygon geometry."""
    geo_rings: list[list[tuple[float, float]]] = []
    for ring in rings:
        coords = [svg_to_lonlat(x, y) for x, y in ring]
        if not coords:
            continue
        coords = _unwrap_ring(coords)
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
            props = {
                "id": pid,
                "name": name,
                "osm_id": osm_id,
                "layer": group_id,
                "fill-opacity": 0.5,
            }
            fill = path_el.get("fill")
            if fill:
                props["fill"] = fill
            features.append(
                {
                    "type": "Feature",
                    "geometry": geometry,
                    "properties": props,
                }
            )

    geojson = {
        "type": "FeatureCollection",
        "features": features,
        "metadata": {
            "source": str(svg_path),
            "projection": "Winkel Tripel",
            "svg_maxx": _SVG_MAXX,
            "svg_maxy": _SVG_MAXY,
            "center_lon": _CENTER_LON,
            "y_center_offset": _Y_CENTER_OFFSET,
            "note": (
                "Winkel Tripel projection centered at 11°E. "
                "Y-center offset of 22 px calibrated from the 49°N US-Canada "
                "border and island-territory label positions. "
                "Post-projection correction mesh (correction_mesh.json) built "
                "from 83k WHM vs admin0 land-border control points (IDW radius 3°). "
                "Residuals after mesh: <0.1° on key straight borders."
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
