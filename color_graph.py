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

from graph_coloring import build_adjacency, greedy_color


def _log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


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

    _log(
        f"Loaded {len(graph['nodes']):,} nodes and {len(graph['edges']):,} edges from {args.graph}"
    )

    adjacency = build_adjacency(graph)
    coloring = greedy_color(adjacency)

    num_colors = max(coloring.values()) + 1 if coloring else 0
    color_counts = [0] * num_colors
    for c in coloring.values():
        color_counts[c] += 1

    _log(f"Coloring used {num_colors} colors:")
    for i, count in enumerate(color_counts):
        _log(f"  color {i}: {count:,} nodes")

    # Verify no adjacent pair shares a color
    violations = 0
    for a, b in graph["edges"]:
        if coloring.get(a) == coloring.get(b):
            _log(f"  VIOLATION: nodes {a} and {b} share color {coloring.get(a)}")
            violations += 1
    if violations == 0:
        _log("Verification passed: no adjacent nodes share a color.")
    else:
        _log(f"WARNING: {violations} violations found!")

    # JSON requires string keys
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(
            {str(k): v for k, v in coloring.items()}, f, ensure_ascii=False, indent=2
        )
    _log(f"Wrote coloring to {args.output}")


if __name__ == "__main__":
    main()
