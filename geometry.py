"""Geometry helpers for OSM ring-building and orientation."""

from collections import defaultdict


def shoelace_signed_area(coords: list[tuple[float, float]]) -> float:
    """Return the signed area of a polygon via the shoelace formula.

    Positive → counter-clockwise (right-hand rule for geographic coords).

    The formula sums trapezoid areas:
        2A = Σ (x_i+1 - x_i)(y_i+1 + y_i)
    Negated because geographic lat increases upward (opposite to screen Y).
    """
    n = len(coords)
    if n < 3:
        return 0.0
    area = 0.0
    for i in range(n):
        x1, y1 = coords[i]
        x2, y2 = coords[(i + 1) % n]
        area += (x2 - x1) * (y2 + y1)
    return -area


def ring_is_ccw(coords: list[tuple[float, float]]) -> bool:
    """Return True if the ring follows the right-hand rule (CCW in geographic coords)."""
    return shoelace_signed_area(coords) > 0


def way_coords_forward(
    way_id: int, way_coords: dict[int, list[tuple[float, float]]]
) -> list[tuple[float, float]]:
    """Return coords for *way_id* (positive) or reversed (negative way_id)."""
    if way_id > 0:
        return way_coords[way_id]
    return list(reversed(way_coords[-way_id]))


def ring_coords(
    signed_way_ids: list[int],
    way_coords: dict[int, list[tuple[float, float]]],
) -> list[tuple[float, float]]:
    """Reconstruct the coordinate ring for an ordered list of (possibly negated) way IDs.

    Adjacent ways share an endpoint, so we skip the duplicate node between segments.
    """
    coords: list[tuple[float, float]] = []
    for i, wid in enumerate(signed_way_ids):
        wcoords = way_coords_forward(wid, way_coords)
        if i == 0:
            coords.extend(wcoords)
        else:
            coords.extend(wcoords[1:])
    return coords


def build_rings(
    way_ids: list[int],
    way_nodes: dict[int, list[int]],
    way_coords: dict[int, list[tuple[float, float]]],
    warn=None,
) -> list[list[int]]:
    """Order ways in a relation into closed, right-hand-rule oriented rings.

    Returns a list of rings; each ring is an ordered list of signed way IDs
    (negative means the way is traversed in reverse).

    Ways that are already closed (first node == last node) form their own rings.
    Open ways are chained by shared endpoints until each ring closes.

    *warn* is an optional callable(str) used to emit warnings; defaults to no-op.
    """
    if warn is None:
        warn = lambda msg: None  # noqa: E731

    # Separate closed and open ways; skip ways we failed to collect
    closed: list[int] = []
    open_ways: list[int] = []
    for wid in way_ids:
        if wid not in way_nodes:
            continue  # missing way – skip
        nodes = way_nodes[wid]
        if len(nodes) >= 2 and nodes[0] == nodes[-1]:
            closed.append(wid)
        else:
            open_ways.append(wid)

    rings: list[list[int]] = []

    # Each closed way is its own ring
    for wid in closed:
        rings.append([wid])

    # Chain open ways into rings by matching endpoints
    if open_ways:
        remaining = set(open_ways)

        # endpoint node_id → list of way_ids that touch that node
        endpoint_index: dict[int, list[int]] = defaultdict(list)
        for wid in open_ways:
            nodes = way_nodes[wid]
            endpoint_index[nodes[0]].append(wid)
            endpoint_index[nodes[-1]].append(wid)

        while remaining:
            seed = next(iter(remaining))
            remaining.remove(seed)
            ring: list[int] = [seed]
            seed_nodes = way_nodes[seed]
            ring_start = seed_nodes[0]
            current_tail = seed_nodes[-1]

            while current_tail != ring_start:
                candidates = [
                    wid for wid in endpoint_index[current_tail] if wid in remaining
                ]
                if not candidates:
                    warn(f"could not close ring (stuck at node {current_tail})")
                    break
                next_wid = candidates[0]
                remaining.remove(next_wid)
                next_nodes = way_nodes[next_wid]
                if next_nodes[0] == current_tail:
                    ring.append(next_wid)
                    current_tail = next_nodes[-1]
                else:
                    ring.append(-next_wid)
                    current_tail = next_nodes[0]

            rings.append(ring)

    # Apply right-hand rule: each ring should be CCW in geographic coordinates
    oriented: list[list[int]] = []
    for ring in rings:
        coords = ring_coords(ring, way_coords)
        if not ring_is_ccw(coords):
            ring = [-wid for wid in reversed(ring)]
        oriented.append(ring)

    return oriented


def _point_in_ring(
    point: tuple[float, float],
    coords: list[tuple[float, float]],
) -> bool:
    """Ray-casting point-in-polygon test."""
    px, py = point
    inside = False
    n = len(coords)
    j = n - 1
    for i in range(n):
        xi, yi = coords[i]
        xj, yj = coords[j]
        if ((yi > py) != (yj > py)) and (px < (xj - xi) * (py - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside


def build_polygon_rings(
    outer_way_ids: list[int],
    inner_way_ids: list[int],
    way_nodes: dict[int, list[int]],
    way_coords: dict[int, list[tuple[float, float]]],
    warn=None,
) -> list[list[list[int]]]:
    """Build a MultiPolygon ring structure from outer and inner (hole) ways.

    Returns a list of polygons. Each polygon is a list whose first element is
    the outer ring (list of signed way IDs) and whose subsequent elements are
    inner rings (holes).  Inner rings are oriented CW (clockwise) to follow the
    GeoJSON right-hand rule for holes.

    Containment is determined geometrically: each inner ring is assigned to the
    smallest outer ring that contains it.
    """
    if warn is None:
        warn = lambda msg: None  # noqa: E731

    # Build outer rings (CCW)
    outer_rings = build_rings(outer_way_ids, way_nodes, way_coords, warn=warn)

    # Build inner rings, then flip to CW (negate each way and reverse list)
    raw_inner = build_rings(inner_way_ids, way_nodes, way_coords, warn=warn)
    inner_rings: list[list[int]] = [[-wid for wid in reversed(r)] for r in raw_inner]

    # Pre-compute a representative point (first coord of first way) for each inner ring
    def ring_representative(ring: list[int]) -> tuple[float, float]:
        first_wid = abs(ring[0])
        wc = way_coords.get(first_wid)
        if wc:
            return wc[0]
        return (0.0, 0.0)

    # Pre-compute coords for each outer ring (for containment test)
    outer_coords_list = [ring_coords(r, way_coords) for r in outer_rings]

    # Assign each inner ring to the smallest outer that contains it
    # "smallest" = smallest absolute area (most specific container)
    outer_areas = [abs(shoelace_signed_area(c)) for c in outer_coords_list]

    # polygons[i] = [outer_ring, ...inner_rings]
    polygons: list[list[list[int]]] = [[r] for r in outer_rings]

    for inner_ring in inner_rings:
        pt = ring_representative(inner_ring)
        best_idx: int | None = None
        best_area = float("inf")
        for i, (oc, area) in enumerate(zip(outer_coords_list, outer_areas)):
            if area < best_area and _point_in_ring(pt, oc):
                best_area = area
                best_idx = i
        if best_idx is not None:
            polygons[best_idx].append(inner_ring)
        else:
            warn(
                f"inner ring starting at way {abs(inner_ring[0])} has no containing outer ring"
            )

    return polygons
