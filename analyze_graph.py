"""Analyze graph structure and attempt better coloring via backtracking + DSatur."""

import json
from collections import Counter, defaultdict


def build_adj(graph):
    adj = defaultdict(set)
    for a, b in graph["edges"]:
        sa, sb = str(a), str(b)
        adj[sa].add(sb)
        adj[sb].add(sa)
    return adj


def greedy_color_order(node_ids, adjacency, order):
    coloring = {}
    for node in order:
        neighbor_colors = {coloring[nb] for nb in adjacency[node] if nb in coloring}
        color = 0
        while color in neighbor_colors:
            color += 1
        coloring[node] = color
    return coloring


def dsatur_color(node_ids, adjacency):
    """DSatur: always color the node with highest saturation (most distinct
    neighbor colors), breaking ties by degree then node ID."""
    coloring = {}
    saturation = {n: 0 for n in node_ids}  # # distinct colors among neighbors
    degree = {n: len(adjacency[n]) for n in node_ids}
    uncolored = set(node_ids)

    while uncolored:
        # Pick node with max saturation, break ties by degree, then node ID
        node = max(uncolored, key=lambda n: (saturation[n], degree[n], n))
        uncolored.remove(node)

        neighbor_colors = {coloring[nb] for nb in adjacency[node] if nb in coloring}
        color = 0
        while color in neighbor_colors:
            color += 1
        coloring[node] = color

        # Update saturation of uncolored neighbors
        for nb in adjacency[node]:
            if nb in uncolored:
                nb_neighbor_colors = {
                    coloring[x] for x in adjacency[nb] if x in coloring
                }
                saturation[nb] = len(nb_neighbor_colors)

    return coloring


def find_cliques_bron_kerbosch(adj, node_ids, max_clique_size=10, time_limit=5.0):
    """Find the maximum clique size via Bron-Kerbosch with pivoting.
    Stops early if a clique of max_clique_size is found or time_limit exceeded."""
    import time

    deadline = time.monotonic() + time_limit
    best = [0]
    best_clique = [[]]

    def bk(R, P, X):
        if time.monotonic() > deadline:
            return
        if not P and not X:
            if len(R) > best[0]:
                best[0] = len(R)
                best_clique[0] = list(R)
            return
        if len(R) + len(P) <= best[0]:
            return  # prune
        if best[0] >= max_clique_size:
            return
        # Pivot: choose vertex in P∪X with most neighbors in P
        pivot = max(P | X, key=lambda v: len(adj[v] & P))
        for v in list(P - adj[pivot]):
            bk(R | {v}, P & adj[v], X & adj[v])
            P.remove(v)
            X.add(v)

    # Order nodes by degree for better pruning
    ordered = sorted(node_ids, key=lambda n: len(adj[n]), reverse=True)
    P_all = set(node_ids)
    for v in ordered:
        if time.monotonic() > deadline:
            break
        bk({v}, P_all & adj[v], set())
        P_all.discard(v)

    return best[0], best_clique[0]


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--graph", default="graph.json")
    args = parser.parse_args()

    graph = json.load(open(args.graph, encoding="utf-8"))
    node_ids = list(graph["nodes"].keys())
    adj = build_adj(graph)

    # --- Degree stats ---
    degrees = sorted(len(adj[n]) for n in node_ids)
    print(f"Nodes: {len(node_ids)}, Edges: {len(graph['edges'])}")
    print(
        f"Degree: min={degrees[0]}, median={degrees[len(degrees) // 2]}, max={degrees[-1]}"
    )
    isolated = sum(1 for d in degrees if d == 0)
    print(f"Isolated nodes (degree 0): {isolated}")

    deg_counts = Counter(degrees)
    print("Degree histogram (degree: count):")
    for d in sorted(deg_counts):
        print(f"  {d:4d}: {deg_counts[d]}")

    # --- Coloring comparisons ---
    print()
    print("=== Coloring approaches ===")

    # Welsh-Powell (degree descending)
    wp_order = sorted(node_ids, key=lambda n: (-len(adj[n]), n))
    wp = greedy_color_order(node_ids, adj, wp_order)
    print(f"Welsh-Powell (degree desc):  {max(wp.values()) + 1} colors")

    # Greedy in random order (averaged)
    import random

    random.seed(42)
    best_random = None
    for _ in range(20):
        order = node_ids[:]
        random.shuffle(order)
        c = greedy_color_order(node_ids, adj, order)
        n = max(c.values()) + 1
        if best_random is None or n < best_random:
            best_random = n
    print(f"Greedy random (best of 20):  {best_random} colors")

    # DSatur
    dsat = dsatur_color(node_ids, adj)
    print(f"DSatur:                      {max(dsat.values()) + 1} colors")

    # --- Clique lower bound ---
    print()
    print("=== Clique lower bound (max 5s search) ===")
    clique_size, clique = find_cliques_bron_kerbosch(adj, node_ids, time_limit=5.0)
    print(f"Largest clique found: {clique_size}  (ids: {[int(x) for x in clique]})")
    print(f"Chromatic number >= {clique_size}")

    # --- Top-degree nodes ---
    print()
    print("Top 10 highest-degree nodes:")
    top = sorted(node_ids, key=lambda n: -len(adj[n]))[:10]
    for n in top:
        members = graph["nodes"][n]["members"]
        print(f"  node {n}: degree={len(adj[n])}, members={members}")

    # --- Are the top-degree nodes mutually adjacent? ---
    print()
    print("Mutual adjacency among top-10 high-degree nodes:")
    for i in range(len(top)):
        for j in range(i + 1, len(top)):
            a, b = top[i], top[j]
            connected = b in adj[a]
            print(f"  {a} -- {b}: {'YES' if connected else 'no'}")

    # --- Subgraph induced by top-N nodes: what's the clique number? ---
    print()
    n_top = 20
    top20 = sorted(node_ids, key=lambda n: -len(adj[n]))[:n_top]
    sub_adj = {n: adj[n] & set(top20) for n in top20}
    clique20, _ = find_cliques_bron_kerbosch(sub_adj, top20, time_limit=2.0)
    print(f"Clique number among top-{n_top} degree nodes: {clique20}")
    print(f"  (These nodes need >= {clique20} different colors among themselves)")

    # --- Simulate removing the top-k nodes and re-coloring the rest ---
    print()
    print("Coloring cost without top-k highest-degree nodes:")
    for k in [1, 5, 10, 20]:
        top_k = set(sorted(node_ids, key=lambda n: -len(adj[n]))[:k])
        rest = [n for n in node_ids if n not in top_k]
        rest_adj = {n: adj[n] - top_k for n in rest}
        c = greedy_color_order(
            rest, rest_adj, sorted(rest, key=lambda n: (-len(rest_adj[n]), n))
        )
        nc = max(c.values()) + 1 if c else 0
        print(f"  remove top {k:2d}: {len(rest)} nodes remaining, {nc} colors")


if __name__ == "__main__":
    main()
