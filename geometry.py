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
