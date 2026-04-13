#!/usr/bin/env python3
"""
Build a (delta_lon, delta_lat) correction mesh from WHM vs admin0.

Every land-border vertex in WA2014.geojson is matched to its nearest
neighbour on the same country's boundary in admin0.geojson.  The offsets
(admin0 position − WHM position) are then interpolated onto a regular 1°
grid using inverse-distance weighting.

The resulting mesh is written to whm/correction_mesh.json and is applied
as a post-projection correction in unproject.py.

Usage:
    python whm/build_mesh.py                           # writes correction_mesh.json
    python whm/build_mesh.py --plot                    # also plots the offset field
"""
import json
import math
import argparse
from pathlib import Path
from collections import defaultdict

# ── Name-matching table (WHM name → admin0 NAME, lower-cased) ─────────────────
ALIASES: dict[str, str] = {
    'america':        'united states of america',
    'alaska':         'united states of america',
    'aleutians':      'united states of america',
    'hawaii':         'united states of america',
    'britain':        'united kingdom',
    'czech':          'czechia',
    'slovak':         'slovakia',
    'kazak':          'kazakhstan',
    'kirgiz':         'kyrgyzstan',
    'tadjik':         'tajikistan',
    'turkmen':        'turkmenistan',
    'uzbeg':          'uzbekistan',
    'rumania':        'romania',
    'moldavia':       'moldova',
    'macedonia':      'north macedonia',
    'bosnia':         'bosnia and herzegovina',
    'kossovo':        'kosovo',
    'ivory coast':    "côte d'ivoire",
    'central africa': 'central african republic',
    'zaire':          'democratic republic of the congo',
    'congo2':         'republic of congo',
    'swazi':          'eswatini',
    'surinam':        'suriname',
    'saudi':          'saudi arabia',
    'korea':          'south korea',
    'timor':          'east timor',
    'papua':          'papua new guinea',
    'luxemburg':      'luxembourg',
    'mbini':          'equatorial guinea',
    'bissau':         'guinea-bissau',
    'south sudan':    'south sudan',
}

def match_name(whm_name: str) -> str:
    n = whm_name.lower()
    return ALIASES.get(n, n)


# ── Geometry helpers ───────────────────────────────────────────────────────────

def feature_verts(feature: dict) -> list[tuple[float, float]]:
    """Flatten all polygon rings to a list of (lon, lat) tuples."""
    coords = feature['geometry']['coordinates']
    gtype  = feature['geometry']['type']
    if gtype == 'Polygon':
        rings = coords
    else:  # MultiPolygon
        rings = [r for poly in coords for r in poly]
    return [(pt[0], pt[1]) for ring in rings for pt in ring]


def dist2(a: tuple, b: tuple) -> float:
    return (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2


# ── Spatial grid index ─────────────────────────────────────────────────────────

class GridIndex:
    """Bucket vertices into 1°×1° cells for fast neighbour lookup."""

    def __init__(self, radius: float = 1.0):
        self.radius = radius
        self.cells: dict[tuple[int, int], list] = defaultdict(list)

    def insert(self, lon: float, lat: float, payload):
        self.cells[(int(math.floor(lon)), int(math.floor(lat)))].append(
            (lon, lat, payload))

    def query(self, lon: float, lat: float) -> list:
        """Return all entries within self.radius of (lon, lat)."""
        r = self.radius
        result = []
        i0, j0 = int(math.floor(lon - r)), int(math.floor(lat - r))
        i1, j1 = int(math.floor(lon + r)), int(math.floor(lat + r))
        for i in range(i0, i1 + 1):
            for j in range(j0, j1 + 1):
                for vlon, vlat, payload in self.cells.get((i, j), []):
                    if abs(vlon - lon) <= r and abs(vlat - lat) <= r:
                        result.append((vlon, vlat, payload))
        return result


# ── Control-point extraction ───────────────────────────────────────────────────

def extract_control_points(
    whm_features: list,
    admin0_features: list,
    land_border_radius: float = 0.25,
    match_radius: float = 3.0,
) -> list[tuple[float, float, float, float]]:
    """
    Return a list of (whm_lon, whm_lat, delta_lon, delta_lat) control points.

    A WHM vertex is accepted as a land-border vertex if any vertex of a
    *different* WHM country lies within `land_border_radius` degrees of it.
    It is then matched to the nearest *land-border* vertex on the same
    country's admin0 boundary (i.e. also within `land_border_radius` of
    another admin0 country), within `match_radius` degrees.

    Requiring both endpoints to be land-border vertices prevents spurious
    matches to coastline vertices in admin0.
    """
    # Build name lookup for admin0
    admin0_by_name: dict[str, dict] = {}
    for f in admin0_features:
        admin0_by_name[f['properties']['NAME'].lower()] = f

    # ── Identify admin0 land-border vertices ────────────────────────────────
    # A vertex of admin0 country A is a "land border" vertex if it is within
    # land_border_radius of any vertex of a *different* admin0 country B.
    print('  Identifying admin0 land-border vertices…')
    admin0_all_idx = GridIndex(radius=land_border_radius)
    for f in admin0_features:
        cname = f['properties']['NAME'].lower()
        for lon, lat in feature_verts(f):
            admin0_all_idx.insert(lon, lat, cname)

    # Build per-country LAND-BORDER vertex index for admin0
    admin0_lb_idx: dict[str, GridIndex] = {}
    for f in admin0_features:
        name = f['properties']['NAME'].lower()
        idx  = GridIndex(radius=match_radius)
        for lon, lat in feature_verts(f):
            # Accept only if another admin0 country is nearby
            neighbours = admin0_all_idx.query(lon, lat)
            if any(
                n[2] != name
                and dist2((lon, lat), (n[0], n[1])) < land_border_radius ** 2
                for n in neighbours
            ):
                idx.insert(lon, lat, None)
        admin0_lb_idx[name] = idx

    # ── WHM land-border vertex index ─────────────────────────────────────────
    whm_all_idx = GridIndex(radius=land_border_radius)
    for f in whm_features:
        cname = f['properties']['name'].lower()
        for lon, lat in feature_verts(f):
            whm_all_idx.insert(lon, lat, cname)

    # ── Extract control points ────────────────────────────────────────────────
    control: list[tuple[float, float, float, float]] = []

    for f in whm_features:
        whm_name   = f['properties']['name'].lower()
        admin_name = match_name(whm_name)
        if admin_name not in admin0_lb_idx:
            continue

        a0_lb_idx = admin0_lb_idx[admin_name]
        verts      = feature_verts(f)

        for lon, lat in verts:
            # Is this WHM vertex on a land border?
            neighbours = whm_all_idx.query(lon, lat)
            is_land_border = any(
                n[2] != whm_name
                and dist2((lon, lat), (n[0], n[1])) < land_border_radius ** 2
                for n in neighbours
            )
            if not is_land_border:
                continue

            # Find nearest admin0 LAND-BORDER vertex for this country
            candidates = a0_lb_idx.query(lon, lat)
            if not candidates:
                continue

            nearest = min(candidates, key=lambda c: dist2((lon, lat), (c[0], c[1])))
            n_lon, n_lat, _ = nearest

            # Accept if the match is within half the search radius
            if dist2((lon, lat), (n_lon, n_lat)) > (match_radius / 2) ** 2:
                continue

            control.append((lon, lat, n_lon - lon, n_lat - lat))

    return control


# ── IDW mesh interpolation ─────────────────────────────────────────────────────

def build_grid(
    control: list[tuple[float, float, float, float]],
    lon_min: int = -180, lon_max: int = 179,
    lat_min: int = -90,  lat_max: int = 89,
    idw_radius: float = 3.0,
    idw_power:  float = 2.0,
) -> dict:
    """
    Interpolate control points onto a 1° grid using inverse-distance weighting.

    Returns a dict with keys 'dlon' and 'dlat', each a list-of-lists
    [lat_idx][lon_idx] with lat_idx = lat - lat_min, lon_idx = lon - lon_min.
    """
    nlons = lon_max - lon_min + 1
    nlats = lat_max - lat_min + 1

    cp_grid2: dict[tuple[int, int], list] = defaultdict(list)
    for clon, clat, dlon, dlat in control:
        cp_grid2[(int(math.floor(clon)), int(math.floor(clat)))].append(
            (clon, clat, dlon, dlat))

    r = idw_radius
    dlon_grid = [[0.0] * nlons for _ in range(nlats)]
    dlat_grid = [[0.0] * nlons for _ in range(nlats)]

    for li, lat in enumerate(range(lat_min, lat_max + 1)):
        for lj, lon in enumerate(range(lon_min, lon_max + 1)):
            # Gather nearby control points
            i0, j0 = int(math.floor(lon - r)), int(math.floor(lat - r))
            i1, j1 = int(math.floor(lon + r)), int(math.floor(lat + r))
            wsum, wdlon, wdlat = 0.0, 0.0, 0.0
            for ci in range(i0, i1 + 1):
                for cj in range(j0, j1 + 1):
                    for clon, clat, cdlon, cdlat in cp_grid2.get((ci, cj), []):
                        d2 = (clon - lon) ** 2 + (clat - lat) ** 2
                        if d2 == 0.0:
                            wsum = 1.0; wdlon = cdlon; wdlat = cdlat
                            break
                        if d2 > r * r:
                            continue
                        w = 1.0 / d2 ** (idw_power / 2)
                        wsum  += w
                        wdlon += w * cdlon
                        wdlat += w * cdlat
            if wsum > 0:
                dlon_grid[li][lj] = wdlon / wsum
                dlat_grid[li][lj] = wdlat / wsum

    return {
        'lon_min': lon_min, 'lon_max': lon_max,
        'lat_min': lat_min, 'lat_max': lat_max,
        'dlon': dlon_grid,
        'dlat': dlat_grid,
    }


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--whm',    default='whm/WA2014.geojson')
    ap.add_argument('--admin0', default='whm/admin0.geojson')
    ap.add_argument('--out',    default='whm/correction_mesh.json')
    ap.add_argument('--plot',   action='store_true')
    args = ap.parse_args()

    print('Loading GeoJSON files…')
    whm_features    = json.loads(Path(args.whm).read_text())['features']
    admin0_features = json.loads(Path(args.admin0).read_text())['features']

    print('Extracting control points…')
    control = extract_control_points(whm_features, admin0_features)
    print(f'  {len(control)} control points')

    # Quick stats
    dlons = [c[2] for c in control]
    dlats = [c[3] for c in control]
    print(f'  delta_lon: mean={sum(dlons)/len(dlons):+.3f}°  '
          f'rms={math.sqrt(sum(d**2 for d in dlons)/len(dlons)):.3f}°')
    print(f'  delta_lat: mean={sum(dlats)/len(dlats):+.3f}°  '
          f'rms={math.sqrt(sum(d**2 for d in dlats)/len(dlats)):.3f}°')

    print('Building 1° correction grid (IDW)…')
    grid = build_grid(control)

    print(f'Writing {args.out}…')
    Path(args.out).write_text(json.dumps(grid, separators=(',', ':')))
    size_kb = Path(args.out).stat().st_size / 1024
    print(f'  {size_kb:.0f} KB')

    if args.plot:
        try:
            import numpy as np
            import matplotlib.pyplot as plt

            dlon_arr = np.array(grid['dlon'])
            dlat_arr = np.array(grid['dlat'])
            lons = range(grid['lon_min'], grid['lon_max'] + 1)
            lats = range(grid['lat_min'], grid['lat_max'] + 1)
            L, B = np.meshgrid(lons, lats)

            fig, axes = plt.subplots(1, 2, figsize=(16, 6))
            for ax, arr, title, clim in zip(
                axes,
                [dlon_arr, dlat_arr],
                ['Δlon (°)', 'Δlat (°)'],
                [0.5, 0.5],
            ):
                im = ax.pcolormesh(L, B, arr, cmap='RdBu_r',
                                   vmin=-clim, vmax=clim)
                plt.colorbar(im, ax=ax)
                ax.set_title(title)
                ax.set_xlabel('Longitude')
                ax.set_ylabel('Latitude')
            plt.tight_layout()
            plt.savefig('whm/correction_mesh.png', dpi=150)
            print('  Saved whm/correction_mesh.png')
        except ImportError:
            print('  (matplotlib/numpy not available; skipping plot)')


if __name__ == '__main__':
    main()
