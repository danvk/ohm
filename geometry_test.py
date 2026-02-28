"""Unit tests for geometry.py helpers."""

import math

from geometry import build_rings, shoelace_signed_area

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


def test_build_rings_empty():
    rings = build_rings([], {}, {})
    assert rings == []
