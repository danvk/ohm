"""Unit tests for geometry.py helpers."""

import math

from extract_for_web import _kept_indices
from geometry import (
    OpenRingWarning,
    UncontainedInnerRingWarning,
    build_polygon_rings,
    build_rings,
    rdp_simplify,
    shoelace_signed_area,
    vw_simplify,
)

# ---------------------------------------------------------------------------
# rdp_simplify
# ---------------------------------------------------------------------------


def test_rdp_short_sequences_unchanged():
    """0-, 1-, and 2-point sequences are returned as-is."""
    assert rdp_simplify([]) == []
    assert rdp_simplify([(0, 0)]) == [(0, 0)]
    assert rdp_simplify([(0, 0), (1, 1)]) == [(0, 0), (1, 1)]


def test_rdp_collinear_interior_removed():
    """Interior points exactly on the line are removed."""
    pts = [(0, 0), (1, 0), (2, 0), (3, 0), (4, 0)]
    result = rdp_simplify(pts, tolerance=0.0)
    assert result == [(0, 0), (4, 0)]


def test_rdp_keeps_endpoints():
    """First and last point are always kept even when collinear."""
    pts = [(0, 0), (5, 0), (10, 0)]
    result = rdp_simplify(pts, tolerance=1.0)
    assert result[0] == (0, 0)
    assert result[-1] == (10, 0)


def test_rdp_significant_deviation_kept():
    """A point that deviates more than the tolerance is retained."""
    # Straight line from (0,0) to (10,0) with a spike at (5,5)
    pts = [(0, 0), (5, 5), (10, 0)]
    result = rdp_simplify(pts, tolerance=1.0)
    assert (5, 5) in result


def test_rdp_within_tolerance_removed():
    """A point that deviates by less than tolerance is removed."""
    # Point (5,0) is exactly on the line (0,0)→(10,0), so distance = 0
    pts = [(0, 0), (5, 0), (10, 0)]
    result = rdp_simplify(pts, tolerance=1.0)
    assert result == [(0, 0), (10, 0)]


def test_rdp_zigzag_all_kept():
    """All points of a zigzag well above tolerance are preserved."""
    pts = [(0, 0), (1, 10), (2, 0), (3, 10), (4, 0)]
    result = rdp_simplify(pts, tolerance=1.0)
    assert result == pts


def test_rdp_mixed_remove_some_keep_some():
    """Near-collinear interior points are removed; significant ones kept."""
    # Points: straight line with a tiny wiggle at (2,1) and a big spike at (5,20)
    pts = [(0, 0), (2, 1), (5, 20), (8, 1), (10, 0)]
    result = rdp_simplify(pts, tolerance=2.0)
    # (5,20) is far from the (0,0)→(10,0) line → kept
    assert (5, 20) in result
    # (2,1) and (8,1) are close to their enclosing segment → removed
    assert (2, 1) not in result
    assert (8, 1) not in result


# ---------------------------------------------------------------------------
# vw_simplify
# ---------------------------------------------------------------------------


def test_vw_short_sequences_unchanged():
    """0-, 1-, and 2-point sequences are returned as-is."""
    assert vw_simplify([]) == []
    assert vw_simplify([(0, 0)]) == [(0, 0)]
    assert vw_simplify([(0, 0), (1, 1)]) == [(0, 0), (1, 1)]


def test_vw_collinear_interior_removed():
    """A collinear interior point (triangle area = 0) is removed."""
    pts = [(0, 0), (5, 0), (10, 0)]
    result = vw_simplify(pts, tolerance=0.0)
    assert result == [(0, 0), (10, 0)]


def test_vw_keeps_endpoints_open():
    """First and last points of an open polyline are always kept."""
    pts = [(0, 0), (5, 0), (10, 0)]
    result = vw_simplify(pts, tolerance=1.0)
    assert result[0] == (0, 0)
    assert result[-1] == (10, 0)


def test_vw_significant_point_kept():
    """A point forming a large triangle is retained."""
    # Triangle area for (0,0)-(5,10)-(10,0) = 0.5 * base * height = 50
    pts = [(0, 0), (5, 10), (10, 0)]
    result = vw_simplify(pts, tolerance=1.0)
    assert (5, 10) in result


def test_vw_removes_small_triangle():
    """A point forming a triangle below the threshold is removed."""
    # (5,1) forms triangle area 0.5*10*1 = 5; tolerance=10 removes it
    pts = [(0, 0), (5, 1), (10, 0)]
    result = vw_simplify(pts, tolerance=10.0)
    assert result == [(0, 0), (10, 0)]


def test_vw_closed_ring_stays_closed():
    """A closed ring (pts[0]==pts[-1]) remains closed after simplification."""
    # Oval-ish ring
    pts = [
        (0, 5),
        (2, 9),
        (5, 10),
        (8, 9),
        (10, 5),
        (8, 1),
        (5, 0),
        (2, 1),
        (0, 5),
    ]
    result = vw_simplify(pts, tolerance=1.0)
    assert result[0] == result[-1]
    assert len(result) >= 3


def test_vw_closed_ring_not_collapsed():
    """A small island ring keeps enough points to cover its bounding box at 100m tolerance."""
    # Quantized coords of way 200757260 (~3.3 km wide island)
    locs = [
        (613350, 725674),
        (613336, 725708),
        (613332, 725755),
        (613329, 725804),
        (613341, 725829),
        (613369, 725847),
        (613433, 725856),
        (613511, 725868),
        (613552, 725870),
        (613583, 725866),
        (613614, 725852),
        (613640, 725830),
        (613656, 725799),
        (613661, 725772),
        (613652, 725741),
        (613617, 725702),
        (613551, 725661),
        (613502, 725645),
        (613444, 725626),
        (613382, 725626),
        (613355, 725641),
        (613350, 725674),
    ]
    # tolerance = 100 m² / 100 = 1.0 unit²
    result = vw_simplify(locs, tolerance=1.0)
    assert result[0] == result[-1], "ring must stay closed"
    assert len(result) >= 6, "should retain enough detail"
    xs = [x for x, _ in result]
    ys = [y for _, y in result]
    x_span = max(xs) - min(xs)
    y_span = max(ys) - min(ys)
    orig_xs = [x for x, _ in locs]
    orig_ys = [y for _, y in locs]
    orig_x_span = max(orig_xs) - min(orig_xs)
    orig_y_span = max(orig_ys) - min(orig_ys)
    assert x_span > 0.8 * orig_x_span, "should cover >80% of original x extent"
    assert y_span > 0.8 * orig_y_span, "should cover >80% of original y extent"


def test_vw_monotone_removal_order():
    """Points are removed in order of increasing effective area."""
    # Five-point polyline; middle area is smallest
    pts = [(0, 0), (1, 2), (5, 1), (9, 3), (10, 0)]
    # Verify that reducing tolerance gradually removes points one at a time
    prev_len = len(pts)
    for tol in [0.5, 2.0, 5.0, 20.0]:
        result = vw_simplify(pts, tolerance=tol)
        assert len(result) <= prev_len
        prev_len = len(result)


def test_vw_collinear_ring_no_crash():
    """A closed ring whose interior points are all collinear (area=0) must not crash.

    Regression test: previously raised ``IndexError: list index out of range``
    because all interior points were removed, leaving an empty result list, and
    then ``result[0]`` was accessed to re-close the ring.
    """
    # Five points on the x-axis, closed; every triangle has area 0.
    pts = [(0, 0), (1, 0), (2, 0), (3, 0), (4, 0), (0, 0)]
    result = vw_simplify(pts, tolerance=1.0)
    # Must not crash, must be a valid closed ring with at least 2 unique points
    assert len(result) >= 3  # at least [a, b, a]
    assert result[0] == result[-1]


def test_vw_huge_tolerance_ring_no_crash():
    """A ring simplified with an extremely large tolerance must not crash.

    Regression test: same root cause as test_vw_collinear_ring_no_crash —
    over-aggressive removal emptied the result list before re-closing.
    """
    pts = [(0, 0), (1, 1), (2, 0), (3, 1), (4, 0), (0, 0)]
    result = vw_simplify(pts, tolerance=10_000_000.0)
    assert len(result) >= 3
    assert result[0] == result[-1]


# ---------------------------------------------------------------------------
# shoelace_signed_area
# ---------------------------------------------------------------------------


def test_shoelace_ccw_square():
    # Unit square traversed counter-clockwise (right-hand rule)
    # (0,0) → (1,0) → (1,1) → (0,1)
    coords = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]
    area = shoelace_signed_area(coords)
    assert area > 0
    assert math.isclose(area, 2.0)  # 2× the signed area = 2×1 = 2


def test_shoelace_cw_square():
    # Same square traversed clockwise — area should be negative
    coords = [(0.0, 0.0), (0.0, 1.0), (1.0, 1.0), (1.0, 0.0)]
    area = shoelace_signed_area(coords)
    assert area < 0
    assert math.isclose(area, -2.0)


def test_shoelace_triangle():
    # Right triangle with legs of length 3 and 4 → area = 6
    coords = [(0.0, 0.0), (3.0, 0.0), (0.0, 4.0)]
    area = shoelace_signed_area(coords)
    assert area > 0
    assert math.isclose(area, 12.0)  # 2× area = 2×6 = 12


def test_shoelace_too_few_points():
    assert shoelace_signed_area([]) == 0.0
    assert shoelace_signed_area([(0.0, 0.0)]) == 0.0
    assert shoelace_signed_area([(0.0, 0.0), (1.0, 0.0)]) == 0.0


# ---------------------------------------------------------------------------
# build_rings – shared test fixtures
# ---------------------------------------------------------------------------

# A simple CCW square made of four open ways:
#
#   3----2
#   |    |
#   0----1
#
# node IDs:  0=(0,0)  1=(1,0)  2=(1,1)  3=(0,1)
# Traversal order for CCW: 0→1→2→3→0

SQUARE_NODES = {
    0: [0, 1],  # way 0: bottom edge  0→1
    1: [1, 2],  # way 1: right edge   1→2
    2: [2, 3],  # way 2: top edge     2→3
    3: [3, 0],  # way 3: left edge    3→0
}
SQUARE_COORDS = {
    0: [(0.0, 0.0), (1.0, 0.0)],
    1: [(1.0, 0.0), (1.0, 1.0)],
    2: [(1.0, 1.0), (0.0, 1.0)],
    3: [(0.0, 1.0), (0.0, 0.0)],
}


def test_build_rings_open_ways_form_one_ring():
    rings = build_rings([0, 1, 2, 3], SQUARE_NODES, SQUARE_COORDS)
    assert len(rings) == 1
    assert len(rings[0]) == 4


def test_build_rings_ccw_orientation():
    """The produced ring must follow the right-hand rule (CCW)."""
    rings = build_rings([0, 1, 2, 3], SQUARE_NODES, SQUARE_COORDS)
    ring = rings[0]
    # All four ways should appear (possibly with sign)
    assert {abs(w) for w in ring} == {0, 1, 2, 3}
    # Reconstruct coords and check orientation
    from geometry import ring_coords, ring_is_ccw

    coords = ring_coords(ring, SQUARE_COORDS)
    assert ring_is_ccw(coords)


def test_build_rings_reverses_cw_ring():
    """Ways given in clockwise order must be corrected to CCW."""
    # Reverse the square: ways in CW order 3→2→1→0 traversed forward
    cw_nodes = {
        10: [0, 3],  # 0→3
        11: [3, 2],  # 3→2
        12: [2, 1],  # 2→1
        13: [1, 0],  # 1→0
    }
    cw_coords = {
        10: [(0.0, 0.0), (0.0, 1.0)],
        11: [(0.0, 1.0), (1.0, 1.0)],
        12: [(1.0, 1.0), (1.0, 0.0)],
        13: [(1.0, 0.0), (0.0, 0.0)],
    }
    rings = build_rings([10, 11, 12, 13], cw_nodes, cw_coords)
    assert len(rings) == 1
    from geometry import ring_coords, ring_is_ccw

    coords = ring_coords(rings[0], cw_coords)
    assert ring_is_ccw(coords)


def test_build_rings_closed_way():
    """A single closed way (first node == last node) forms its own ring."""
    closed_nodes = {99: [0, 1, 2, 3, 0]}
    closed_coords = {99: [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0), (0.0, 0.0)]}
    rings = build_rings([99], closed_nodes, closed_coords)
    assert len(rings) == 1
    assert rings[0] == [99]  # single way, forward (already CCW)


def test_build_rings_closed_way_cw_gets_negated():
    """A closed way in CW order must be negated."""
    cw_nodes = {99: [0, 3, 2, 1, 0]}
    cw_coords = {99: [(0.0, 0.0), (0.0, 1.0), (1.0, 1.0), (1.0, 0.0), (0.0, 0.0)]}
    rings = build_rings([99], cw_nodes, cw_coords)
    assert len(rings) == 1
    assert rings[0] == [-99]


def test_build_rings_two_rings():
    """Two disjoint closed ways produce two separate rings."""
    # Square A
    nodes_a = {1: [10, 11, 12, 13, 10]}
    coords_a = {1: [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0), (0.0, 0.0)]}
    # Square B (shifted)
    nodes_b = {2: [20, 21, 22, 23, 20]}
    coords_b = {2: [(2.0, 0.0), (3.0, 0.0), (3.0, 1.0), (2.0, 1.0), (2.0, 0.0)]}
    combined_nodes = {**nodes_a, **nodes_b}
    combined_coords = {**coords_a, **coords_b}
    rings = build_rings([1, 2], combined_nodes, combined_coords)
    assert len(rings) == 2


def test_build_rings_reversed_way_needed():
    """One way needs to be reversed to close the ring."""
    # Square where way 2 is stored in reverse (3→2 stored as 2→3 → must be reversed)
    reversed_nodes = {
        0: [0, 1],  # 0→1
        1: [1, 2],  # 1→2
        2: [3, 2],  # stored 3→2, needs reversal to get 2→3
        3: [3, 0],  # 3→0
    }
    reversed_coords = {
        0: [(0.0, 0.0), (1.0, 0.0)],
        1: [(1.0, 0.0), (1.0, 1.0)],
        2: [(0.0, 1.0), (1.0, 1.0)],  # reversed; traversed as -2 → (1,1)→(0,1)
        3: [(0.0, 1.0), (0.0, 0.0)],
    }
    rings = build_rings([0, 1, 2, 3], reversed_nodes, reversed_coords)
    assert len(rings) == 1
    ring = rings[0]
    # Way 2 should appear negated
    assert -2 in ring
    from geometry import ring_coords, ring_is_ccw

    coords = ring_coords(ring, reversed_coords)
    assert ring_is_ccw(coords)


def test_build_rings_missing_way_skipped():
    """Ways not present in way_nodes are silently skipped."""
    rings = build_rings([0, 1, 2, 3, 999], SQUARE_NODES, SQUARE_COORDS)
    assert len(rings) == 1  # still one ring; 999 is simply ignored


def test_build_rings_open_ring_warns():
    """Disconnected ways emit OpenRingWarnings with both stuck endpoint node IDs."""
    # Two ways that don't connect: 0→1 and 2→3 (nodes 1 and 2 are different)
    nodes = {
        0: [0, 1],
        1: [2, 3],
    }
    coords = {
        0: [(0.0, 0.0), (1.0, 0.0)],
        1: [(2.0, 0.0), (3.0, 0.0)],
    }
    warnings = []
    build_rings([0, 1], nodes, coords, warn=warnings.append)
    open_warnings = [w for w in warnings if isinstance(w, OpenRingWarning)]
    assert len(open_warnings) == 2
    # Both endpoints of each disconnected segment appear across the warnings
    all_nodes = {w.node_id_start for w in open_warnings} | {
        w.node_id_end for w in open_warnings
    }
    assert all_nodes == {0, 1, 2, 3}


def test_build_rings_empty():
    rings = build_rings([], {}, {})
    assert rings == []


# ---------------------------------------------------------------------------
# build_polygon_rings – holes support
# ---------------------------------------------------------------------------

# Outer ring: large CCW square  (0,0)→(4,0)→(4,4)→(0,4)
# Inner ring: small square inside it  (1,1)→(3,1)→(3,3)→(1,3)
#
#  0,4 ---- 4,4
#   |  1,3-3,3 |
#   |  |     | |
#   |  1,1-3,1 |
#  0,0 ---- 4,0

OUTER_NODES = {
    10: [100, 101],  # (0,0)→(4,0)
    11: [101, 102],  # (4,0)→(4,4)
    12: [102, 103],  # (4,4)→(0,4)
    13: [103, 100],  # (0,4)→(0,0)
}
OUTER_COORDS = {
    10: [(0.0, 0.0), (4.0, 0.0)],
    11: [(4.0, 0.0), (4.0, 4.0)],
    12: [(4.0, 4.0), (0.0, 4.0)],
    13: [(0.0, 4.0), (0.0, 0.0)],
}
INNER_NODES = {
    20: [200, 201],  # (1,1)→(3,1)
    21: [201, 202],  # (3,1)→(3,3)
    22: [202, 203],  # (3,3)→(1,3)
    23: [203, 200],  # (1,3)→(1,1)
}
INNER_COORDS = {
    20: [(1.0, 1.0), (3.0, 1.0)],
    21: [(3.0, 1.0), (3.0, 3.0)],
    22: [(3.0, 3.0), (1.0, 3.0)],
    23: [(1.0, 3.0), (1.0, 1.0)],
}
ALL_NODES = {**OUTER_NODES, **INNER_NODES}
ALL_COORDS = {**OUTER_COORDS, **INNER_COORDS}


def test_build_polygon_rings_one_polygon_one_hole():
    """One outer ring + one inner ring → one polygon with one hole."""
    polygons, warnings = build_polygon_rings(
        list(OUTER_NODES), list(INNER_NODES), ALL_NODES, ALL_COORDS
    )
    assert len(polygons) == 1
    poly = polygons[0]
    assert len(poly) == 2  # outer + one hole
    assert warnings == []


def test_build_polygon_rings_outer_ccw_inner_cw():
    """Outer ring must be CCW; inner (hole) ring must be CW."""
    from geometry import ring_coords, ring_is_ccw

    polygons, _ = build_polygon_rings(
        list(OUTER_NODES), list(INNER_NODES), ALL_NODES, ALL_COORDS
    )
    poly = polygons[0]
    outer_ring, hole_ring = poly[0], poly[1]

    outer_coords = ring_coords(outer_ring, ALL_COORDS)
    hole_coords = ring_coords(hole_ring, ALL_COORDS)

    assert ring_is_ccw(outer_coords), "outer ring should be CCW"
    assert not ring_is_ccw(hole_coords), "hole ring should be CW"


def test_build_polygon_rings_no_holes():
    """No inner ways → each outer way becomes a polygon with no holes."""
    polygons, _ = build_polygon_rings(list(OUTER_NODES), [], ALL_NODES, ALL_COORDS)
    assert len(polygons) == 1
    assert len(polygons[0]) == 1  # outer ring only


def test_build_polygon_rings_two_outers_one_hole():
    """Two outer rings; hole belongs to the smaller (more specific) outer."""
    from geometry import ring_coords

    # Second outer ring: a large ring far away that also contains the inner ring
    # but is bigger — the inner should still be assigned to the smaller outer.
    # We reuse OUTER as the smaller ring (4×4=16 area).
    # Create a huge outer: (-10,-10)→(20,-10)→(20,20)→(-10,20)
    BIG_OUTER_NODES = {
        30: [300, 301],
        31: [301, 302],
        32: [302, 303],
        33: [303, 300],
    }
    BIG_OUTER_COORDS = {
        30: [(-10.0, -10.0), (20.0, -10.0)],
        31: [(20.0, -10.0), (20.0, 20.0)],
        32: [(20.0, 20.0), (-10.0, 20.0)],
        33: [(-10.0, 20.0), (-10.0, -10.0)],
    }
    combined_nodes = {**ALL_NODES, **BIG_OUTER_NODES}
    combined_coords = {**ALL_COORDS, **BIG_OUTER_COORDS}

    outer_ids = list(OUTER_NODES) + list(BIG_OUTER_NODES)
    inner_ids = list(INNER_NODES)
    polygons, _ = build_polygon_rings(
        outer_ids, inner_ids, combined_nodes, combined_coords
    )

    assert len(polygons) == 2
    # Identify the small vs large outer polygon by coordinate area
    poly_areas = [
        abs(
            sum(
                (
                    ring_coords(p[0], combined_coords)[i][0]
                    - ring_coords(p[0], combined_coords)[
                        (i + 1) % len(ring_coords(p[0], combined_coords))
                    ][0]
                )
                * (
                    ring_coords(p[0], combined_coords)[i][1]
                    + ring_coords(p[0], combined_coords)[
                        (i + 1) % len(ring_coords(p[0], combined_coords))
                    ][1]
                )
                for i in range(len(ring_coords(p[0], combined_coords)))
            )
        )
        / 2
        for p in polygons
    ]
    small_poly = polygons[poly_areas.index(min(poly_areas))]
    large_poly = polygons[poly_areas.index(max(poly_areas))]

    assert len(small_poly) == 2, "hole should be assigned to the smaller outer"
    assert len(large_poly) == 1, "large outer should have no holes"


def test_build_polygon_rings_uncontained_inner_warns():
    """An inner ring with no containing outer ring triggers a warning."""
    # Inner ring is far outside the outer ring
    FAR_INNER_NODES = {
        40: [400, 401],
        41: [401, 402],
        42: [402, 403],
        43: [403, 400],
    }
    FAR_INNER_COORDS = {
        40: [(100.0, 100.0), (102.0, 100.0)],
        41: [(102.0, 100.0), (102.0, 102.0)],
        42: [(102.0, 102.0), (100.0, 102.0)],
        43: [(100.0, 102.0), (100.0, 100.0)],
    }
    combined_nodes = {**OUTER_NODES, **FAR_INNER_NODES}
    combined_coords = {**OUTER_COORDS, **FAR_INNER_COORDS}

    polygons, warnings = build_polygon_rings(
        list(OUTER_NODES),
        list(FAR_INNER_NODES),
        combined_nodes,
        combined_coords,
    )
    assert any(isinstance(w, UncontainedInnerRingWarning) for w in warnings)
    uncontained = [w for w in warnings if isinstance(w, UncontainedInnerRingWarning)]
    assert uncontained[0].way_id in {40, 41, 42, 43}
    # The polygon has only its outer ring; the orphan inner is discarded
    assert len(polygons) == 1
    assert len(polygons[0]) == 1


# ---------------------------------------------------------------------------
# _kept_indices (RDP index recovery)
# ---------------------------------------------------------------------------


def test_kept_indices_basic():
    """Every kept point maps to the correct original index."""
    original = [(0, 0), (1, 0), (2, 0), (3, 0), (4, 0)]
    simplified = [(0, 0), (2, 0), (4, 0)]
    assert _kept_indices(original, simplified) == [0, 2, 4]


def test_kept_indices_endpoints_always_anchored():
    """First simplified point maps to index 0; last maps to index -1."""
    original = [(0, 0), (5, 0), (10, 0)]
    simplified = [(0, 0), (10, 0)]
    indices = _kept_indices(original, simplified)
    assert indices[0] == 0
    assert indices[-1] == 2  # len(original) - 1


def test_kept_indices_duplicate_endpoint_uses_last_occurrence():
    """When the last coordinate appears more than once, the final index is used.

    This was the Angola bug: a way whose last two raw nodes quantize to the
    same grid cell.  A naive forward scan would match simplified[-1] to the
    first (earlier) occurrence, returning the wrong node ID for the endpoint.
    """
    # Simulate: original has a duplicate at the end (two nodes at same quantized loc)
    dup = (10, 0)
    original = [(0, 0), (3, 0), (7, 0), dup, dup]  # indices 3 and 4 are identical
    # RDP keeps first and last: simplified = [(0,0), (10,0)]
    simplified = [(0, 0), dup]
    indices = _kept_indices(original, simplified)
    # Must map to index 0 and index 4 (the true last element), NOT index 3
    assert indices == [0, 4]
