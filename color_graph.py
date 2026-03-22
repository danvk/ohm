"""Color the admin_level=2 connectivity graph using a greedy heuristic.

Reads the graph.json produced by build_connectivity_graph.py and assigns an
integer color (0-based) to each node such that no two adjacent nodes share
the same color.  Uses the Welsh-Powell greedy algorithm: nodes are colored in
descending order of degree, and each node is assigned the lowest color not
already used by any of its already-colored neighbors.

This is not guaranteed to find the chromatic number, but works well in practice
for planar-like geographic graphs (four-color theorem guarantees a solution
exists with ≤4 colors, and greedy on degree order typically achieves that).

Usage:
    python color_graph.py [--graph graph.json] [--output coloring.json]

Output (coloring.json):
    {
      "<node_id>": <color_int>,
      ...
    }
"""

import argparse
import json
import sys
from collections import defaultdict


def _log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


def greedy_color(
    node_ids: list[str],
    adjacency: dict[str, set[str]],
) -> dict[str, int]:
    """Welsh-Powell greedy graph coloring.

    Nodes are processed in descending order of degree.  Each node receives the
    smallest non-negative integer not used by any already-colored neighbor.
    """
    # Sort by degree descending (ties broken by node ID for determinism)
    order = sorted(node_ids, key=lambda n: (-len(adjacency[n]), n))

    coloring: dict[str, int] = {}

    for node in order:
        neighbor_colors = {coloring[nb] for nb in adjacency[node] if nb in coloring}
        color = 0
        while color in neighbor_colors:
            color += 1
        coloring[node] = color

    return coloring


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Greedy graph coloring of the admin_level=2 connectivity graph."
    )
    parser.add_argument(
        "--graph",
        default="graph.json",
        help="Input graph JSON file (default: graph.json)",
    )
    parser.add_argument(
        "--output",
        default="coloring.json",
        help="Output coloring JSON file (default: coloring.json)",
    )
    args = parser.parse_args()

    with open(args.graph, encoding="utf-8") as f:
        graph = json.load(f)

    node_ids: list[str] = list(graph["nodes"].keys())
    edges: list[list[int]] = graph["edges"]

    _log(f"Loaded {len(node_ids):,} nodes and {len(edges):,} edges from {args.graph}")

    # Build adjacency sets (string IDs)
    adjacency: dict[str, set[str]] = defaultdict(set)
    for a, b in edges:
        sa, sb = str(a), str(b)
        adjacency[sa].add(sb)
        adjacency[sb].add(sa)

    coloring = greedy_color(node_ids, adjacency)

    num_colors = max(coloring.values()) + 1 if coloring else 0
    color_counts = [0] * num_colors
    for c in coloring.values():
        color_counts[c] += 1

    _log(f"Coloring used {num_colors} colors:")
    for i, count in enumerate(color_counts):
        _log(f"  color {i}: {count:,} nodes")

    # Verify no adjacent pair shares a color
    violations = 0
    for a, b in edges:
        sa, sb = str(a), str(b)
        if coloring.get(sa) == coloring.get(sb):
            _log(f"  VIOLATION: nodes {sa} and {sb} share color {coloring.get(sa)}")
            violations += 1
    if violations == 0:
        _log("Verification passed: no adjacent nodes share a color.")
    else:
        _log(f"WARNING: {violations} violations found!")

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(coloring, f, ensure_ascii=False, indent=2)
    _log(f"Wrote coloring to {args.output}")


if __name__ == "__main__":
    main()
