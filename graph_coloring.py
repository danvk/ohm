"""Graph coloring utilities shared by color_graph.py and extract_for_web.py."""


def build_adjacency(graph: dict) -> dict[int, set[int]]:
    """Build an integer-keyed adjacency map from a graph.json dict."""
    adj: dict[int, set[int]] = {int(nid): set() for nid in graph["nodes"]}
    for a, b in graph["edges"]:
        adj[a].add(b)
        adj[b].add(a)
    return adj


def greedy_color(adj: dict[int, set[int]]) -> dict[int, int]:
    """Welsh-Powell greedy graph coloring.

    Nodes are processed in descending order of degree (ties broken by node ID
    for determinism).  Each node receives the smallest non-negative integer not
    used by any already-colored neighbor.

    Returns a dict mapping node_id (int) → color (int, 0-based).
    """
    coloring: dict[int, int] = {}
    for node in sorted(adj, key=lambda n: (-len(adj[n]), n)):
        used = {coloring[nb] for nb in adj[node] if nb in coloring}
        color = 0
        while color in used:
            color += 1
        coloring[node] = color
    return coloring
