"""Tool curation: test every registry implementation against NetworkX and keep the best one per tool.

    python curation/curate.py --raw ../tools            # test all, write curation/report.json + report.md
    python curation/curate.py --raw ../tools --install  # also copy the winners into registry/tools/

For each tool name we run every implementation on test cases built from the provided
datasets, compare the output with a NetworkX reference (NetworkX is only used here, never
by the orchestrator or the tools), and score it. Ties are broken by speed on the airports
graph, by how many useful options the manifest offers, and by the description length.
Outputs differ between implementations, so the extractors below search the output for the
values they need instead of assuming one layout.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import networkx as nx  # noqa: E402
from networkx.algorithms import community as nxcom  # noqa: E402

from graphkit import GraphStore  # noqa: E402
from graphkit.loader import load_tool  # noqa: E402
from graphkit.testing import to_networkx  # noqa: E402
from graphkit.validate import validate  # noqa: E402

REL_TOL = 1e-3
STORE = GraphStore()
NX = {gid: to_networkx(STORE.get(gid)) for gid in ("karate", "lesmis", "courses", "projects", "airports")}


# ------------------------------------------------------------------ extractors
def walk(obj, key=None):
    """Yield (key, value) for every value in a nested JSON structure."""
    yield key, obj
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from walk(v, k)
    elif isinstance(obj, list):
        for v in obj:
            yield from walk(v, key)


def is_num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def close(a, b, tol=REL_TOL):
    if not (is_num(a) and is_num(b)):
        return False
    return abs(a - b) <= max(tol * abs(b), 1e-6)


def first_num(out, keys):
    """First numeric value stored under one of `keys` (searched in key order)."""
    for want in keys:
        for k, v in walk(out.get("result")):
            if k == want and is_num(v):
                return v
    return None


def any_num_close(out, value):
    return any(is_num(v) and close(v, value) for _, v in walk(out.get("result")))


def first_bool(out, keys):
    for want in keys:
        for k, v in walk(out.get("result")):
            if k == want and isinstance(v, bool):
                return v
    return None


SCORE_KEYS = ("score", "centrality", "betweenness", "closeness", "pagerank", "authority", "hub",
              "degree_centrality", "value", "coefficient", "clustering", "jaccard", "similarity")


def ranked(out, prefer=SCORE_KEYS):
    """The first list of node dicts in the result, as [(id, score or None)]."""
    for _, v in walk(out.get("result")):
        if isinstance(v, list) and v and all(isinstance(x, dict) and "id" in x for x in v):
            rows = []
            for x in v:
                score = next((x[k] for k in prefer if is_num(x.get(k))), None)
                rows.append((x["id"], score))
            return rows
    return []


def registered_sets(out, exclude=()):
    """Node sets of every subgraph id mentioned in the output (communities, components, ...)."""
    sets, seen = [], set()
    for k, v in walk(out):
        if k in ("graph_id", "result_graph_id", "subgraph_id") and isinstance(v, str) and "~" in v \
                and v not in seen and v not in exclude and STORE.has_graph(v):
            seen.add(v)
            sets.append(frozenset(STORE.get(v).nodes()))
    return sets


def node_ids(obj):
    return [v["id"] for _, v in walk(obj) if isinstance(v, dict) and "id" in v and "label" in v]


# ------------------------------------------------------------------ parameter mapping
SYNONYMS = {
    "node": ["node", "seed_node", "source_node", "start_node", "center", "ego", "source"],
    "source": ["source", "src", "node_a", "node1", "start", "node"],
    "target": ["target", "dest", "sink", "node_b", "node2", "other", "target_node", "end"],
    "k": ["k", "radius", "hops", "depth"],
    "num_communities": ["num_communities", "n_communities", "communities", "k"],
    "direction": ["direction", "mode", "degree_type"],
}


def adapt(params_schema: dict, canonical: dict) -> dict | None:
    """Map canonical argument names onto this implementation's names. None if impossible."""
    args, used = {}, set()
    for key, value in canonical.items():
        if key in ("graph_id",):
            args[key] = value
            continue
        names = SYNONYMS.get(key, [key])
        name = next((n for n in names if n in params_schema and n not in used), None)
        if name is None:
            if key.startswith("?"):  # optional argument
                continue
            return None
        used.add(name)
        args[name] = value
    if "top_k" in params_schema and "top_k" not in args:
        args["top_k"] = 100
    return args


# ------------------------------------------------------------------ references
def ref_rank_check(out, ref: dict, n_expected=10):
    """Fraction of returned (id, score) rows that agree with the reference scores, top rows only."""
    rows = [r for r in ranked(out) if r[1] is not None][:n_expected]
    if len(rows) < min(n_expected, len(ref)):
        return 0.0, f"only {len(rows)} scored rows"
    good = sum(1 for nid, s in rows if nid in ref and close(s, ref[nid]))
    # the returned rows must also be the true top ones
    best = sorted(ref.values(), reverse=True)[:len(rows)]
    order_ok = all(close(rows[i][1], best[i]) for i in range(len(rows)))
    frac = good / len(rows)
    return (frac if order_ok else frac * 0.5), f"{good}/{len(rows)} scores match, order {'ok' if order_ok else 'WRONG'}"


def partition_quality(G, sets):
    nodes = set(G.nodes())
    union = set().union(*sets) if sets else set()
    disjoint = sum(len(s) for s in sets) == len(union)
    if not sets or not disjoint or union != nodes:
        return None
    return nxcom.modularity(G.to_undirected() if G.is_directed() else G, sets, weight="weight")


def case(graph, args, check, label=None):
    return {"graph": graph, "args": args, "check": check, "label": label or f"{graph} {args}"}


def C(graph, canonical, check, label=None):
    return case(graph, {"graph_id": graph, **canonical}, check, label)


def _pr(G, **kw):
    return nx.pagerank(G, weight="weight", tol=1e-12, max_iter=10000, **kw)


def tests_for(name: str):
    K, L, CO, P, A = (NX[g] for g in ("karate", "lesmis", "courses", "projects", "airports"))
    T = []
    if name == "pagerank":
        for g in ("karate", "lesmis", "courses", "airports"):
            ref = _pr(NX[g])
            T.append(C(g, {}, lambda o, r=ref: ref_rank_check(o, r)))
    elif name == "personalized_pagerank":
        for g, s in (("karate", "m1"), ("courses", "CS101"), ("lesmis", "c74")):
            ref = _pr(NX[g], personalization={s: 1.0})
            ref_u = nx.pagerank(NX[g], weight=None, personalization={s: 1.0}, tol=1e-12, max_iter=10000)

            def chk(o, r=ref, ru=ref_u, s=s):
                rows = [x for x in ranked(o) if x[1] is not None and x[0] != s]
                r2 = {k: v for k, v in r.items()}
                a = ref_rank_check({"result": [{"id": i, "score": v} for i, v in rows]}, {k: v for k, v in r2.items() if k != s})
                b = ref_rank_check({"result": [{"id": i, "score": v} for i, v in rows]}, {k: v for k, v in ru.items() if k != s})
                return (a if a[0] >= b[0] else (b[0], b[1] + " (unweighted)"))
            T.append(C(g, {"node": s}, chk))
    elif name == "betweenness_centrality":
        for g in ("karate", "lesmis", "courses"):
            ref = nx.betweenness_centrality(NX[g], normalized=True)
            T.append(C(g, {}, lambda o, r=ref: ref_rank_check(o, r)))
    elif name == "closeness_centrality":
        for g in ("karate", "lesmis", "courses"):
            ref = nx.closeness_centrality(NX[g])

            def chk(o, r=ref):
                rows = ranked(o, prefer=("score", "closeness", "centrality", "value"))
                if len(rows) == 1:  # single-node implementation
                    nid, s = rows[0]
                    return (1.0 if close(s, r[nid]) else 0.0), "single node"
                return ref_rank_check(o, r)
            T.append(C(g, {}, chk))
        # single node query
        ref = nx.closeness_centrality(K)
        T.append(C("karate", {"node": "m34"}, lambda o, r=ref: ((1.0 if any_num_close(o, r["m34"]) else 0.0), "node m34")))
    elif name == "degree_centrality":
        for g in ("karate", "lesmis", "airports"):
            ref = nx.degree_centrality(NX[g])
            deg = dict(NX[g].degree())

            def chk(o, r=ref, d=deg):
                rows = ranked(o, prefer=("score", "centrality", "degree_centrality", "value", "normalized"))
                if rows and all(s is not None for _, s in rows):
                    return ref_rank_check(o, r)
                rows = ranked(o, prefer=("degree",))
                return ref_rank_check({"result": [{"id": i, "score": s} for i, s in rows]}, d)
            T.append(C(g, {}, chk))
    elif name == "degree_distribution":
        for g in ("karate", "airports"):
            G = NX[g]
            hist = {}
            for _, d in G.degree():
                hist[d] = hist.get(d, 0) + 1
            mean = sum(d for _, d in G.degree()) / G.number_of_nodes()

            def chk(o, h=hist, m=mean):
                pts = 0
                pts += 0.5 if any_num_close(o, m) else 0
                mx = max(h)
                pts += 0.5 if first_num(o, ("max_degree", "max")) == mx or any(
                    isinstance(v, list) and len(v) == mx + 1 for _, v in walk(o.get("result"))) else 0
                return pts, f"mean {m:.3f}, max {mx}"
            T.append(C(g, {}, chk))
    elif name == "graph_summary":
        for g in ("karate", "lesmis", "airports", "courses"):
            G = NX[g]
            dens = nx.density(G)

            def chk(o, G=G, dens=dens):
                n = first_num(o, ("nodes", "number_of_nodes", "node_count", "num_nodes", "n_nodes"))
                m = first_num(o, ("edges", "number_of_edges", "edge_count", "num_edges", "n_edges"))
                d = first_num(o, ("density",))
                pts = (n == G.number_of_nodes()) + (m == G.number_of_edges()) + close(d, dens)
                return pts / 3, f"n={n} m={m} density={d}"
            T.append(C(g, {}, chk))
    elif name == "clustering_coefficient":
        for g in ("karate", "lesmis"):
            avg = nx.average_clustering(NX[g])
            T.append(C(g, {}, lambda o, a=avg: ((1.0 if any_num_close(o, a) else 0.0), f"avg {a:.6f}")))
        for g, n in (("karate", "m1"), ("lesmis", "c74")):
            c = nx.clustering(NX[g], n)
            T.append(C(g, {"node": n}, lambda o, c=c: ((1.0 if any_num_close(o, c) else 0.0), f"node {c:.6f}")))
    elif name == "connected_components":
        for g in ("karate", "projects", "courses", "airports"):
            G = NX[g]
            comps = list(nx.weakly_connected_components(G) if G.is_directed() else nx.connected_components(G))

            def chk(o, comps=comps, g=g):
                cnt = first_num(o, ("num_components", "component_count", "number_of_components", "count",
                                    "components_count", "n_components", "total_components"))
                if cnt is None and isinstance(o.get("result"), list):
                    cnt = len(o["result"])
                sets = registered_sets(o, exclude=(g,))
                largest = max(len(c) for c in comps)
                ok_sets = bool(sets) and max(len(s) for s in sets) == largest and set(sets) <= set(map(frozenset, comps))
                return ((cnt == len(comps)) * 0.5 + ok_sets * 0.5), f"count {cnt} vs {len(comps)}, sets {'ok' if ok_sets else 'bad'}"
            T.append(C(g, {}, chk))
    elif name == "strongly_connected_components":
        for g in ("courses", "airports"):
            comps = list(nx.strongly_connected_components(NX[g]))

            def chk(o, comps=comps, g=g):
                cnt = first_num(o, ("num_components", "number_of_components", "component_count", "count", "n_components"))
                sets = registered_sets(o, exclude=(g,))
                largest = max(len(c) for c in comps)
                ok_sets = (not sets) or max(len(s) for s in sets) == largest
                return ((cnt == len(comps)) * 0.7 + ok_sets * 0.3), f"count {cnt} vs {len(comps)}"
            T.append(C(g, {}, chk))
    elif name == "articulation_points_bridges":
        for g in ("karate", "lesmis", "projects"):
            G = NX[g]
            aps = set(nx.articulation_points(G))
            brs = {frozenset(e) for e in nx.bridges(G)}

            def chk(o, aps=aps, brs=brs):
                r = o.get("result") or {}
                ap_list = r.get("articulation_points") if isinstance(r, dict) else None
                got_aps = set(node_ids(ap_list)) if ap_list is not None else None
                nap = first_num(o, ("articulation_point_count", "total_articulation_points", "num_articulation_points",
                                    "articulation_points_count", "n_articulation_points"))
                nbr = first_num(o, ("bridge_count", "total_bridges", "num_bridges", "bridges_count", "n_bridges"))
                pts = 0.5 * (got_aps == aps or (got_aps is not None and got_aps <= aps and nap == len(aps)))
                pts += 0.5 * (nbr == len(brs))
                return pts, f"aps {nap}/{len(aps)} bridges {nbr}/{len(brs)}"
            T.append(C(g, {}, chk))
    elif name == "bipartite_check":
        for g in ("projects", "karate", "courses", "lesmis"):
            truth = nx.is_bipartite(NX[g])
            T.append(C(g, {}, lambda o, t=truth: ((1.0 if first_bool(o, ("is_bipartite", "bipartite")) == t else 0.0), f"truth {t}")))
    elif name == "bipartite_matching":
        G = P
        size = len(nx.bipartite.maximum_matching(G, top_nodes=[n for n in G if n.startswith("P")])) // 2
        T.append(C("projects", {}, lambda o, s=size: ((1.0 if first_num(o, ("matching_size", "size", "num_matches", "max_matching")) == s
                                                        or len((o.get("result") or [])) == s else 0.0), f"size {s}")))
        T.append(C("karate", {}, lambda o: ((1.0 if o.get("status") == "error" else 0.3), "non-bipartite graph should error")))
    elif name == "diameter_eccentricity":
        for g in ("karate", "lesmis"):
            G = NX[g]
            d, r = nx.diameter(G), nx.radius(G)  # in hops
            T.append(C(g, {}, lambda o, d=d, r=r: (0.7 * close(first_num(o, ("diameter",)), d) + 0.3 * (first_num(o, ("radius",)) in (r, None)),
                                                  f"diameter {d} radius {r}")))
        # diameter is undefined on a disconnected graph: an error (or a per-component answer) is fine
        T.append(C("projects", {}, lambda o: ((1.0 if o.get("status") == "error" or first_num(o, ("diameter",)) == 8 else 0.0), "disconnected")))
        ecc = nx.eccentricity(K)

        def chk_ecc(o, e=ecc["m34"]):
            r = o.get("result") or {}
            node = r.get("node") if isinstance(r, dict) else None
            got = node.get("eccentricity") if isinstance(node, dict) else None
            return (1.0 if got == e else 0.0), f"ecc m34 {e}, got {got}"
        T.append(C("karate", {"node": "m34"}, chk_ecc))
    elif name == "ego_network":
        for g, n in (("karate", "m1"), ("airports", "MAA"), ("courses", "CS201")):
            G = NX[g]
            if G.is_directed():
                nb_out = set(G.successors(n)) | {n}
                nb_both = nb_out | set(G.predecessors(n))
            else:
                nb_out = nb_both = set(G.neighbors(n)) | {n}

            def chk(o, a=nb_out, b=nb_both, g=g):
                sets = registered_sets(o, exclude=(g,))
                exact = any(s in (frozenset(a), frozenset(b)) for s in sets)
                return (1.0 if exact else 0.0), f"sizes out {len(a)} both {len(b)} got {[len(s) for s in sets]}"
            T.append(C(g, {"node": n}, chk))
    elif name == "k_hop_neighborhood":
        for g, n, k in (("karate", "m1", 2), ("airports", "MAA", 1), ("courses", "CS101", 2)):
            G = NX[g]
            out_set = set(nx.single_source_shortest_path_length(G, n, cutoff=k)) - {n}
            und = set(nx.single_source_shortest_path_length(G.to_undirected(), n, cutoff=k)) - {n}

            def chk(o, a=out_set, b=und):
                cnt = first_num(o, ("count", "total_reached", "reached", "num_nodes", "n_nodes", "total", "node_count"))
                sets = registered_sets(o)
                # the subgraph may or may not include the start node itself
                exact = any(len(s ^ a) <= 1 or len(s ^ b) <= 1 for s in sets)
                pts = 0.5 * (cnt in (len(a), len(b), len(a) + 1, len(b) + 1)) + 0.5 * exact
                return pts, f"{len(a)} out / {len(b)} undirected; count {cnt}"
            T.append(C(g, {"node": n, "k": k}, chk))
    elif name == "reachability":
        for g, s, t in (("courses", "CS101", "CS401"), ("courses", "CS401", "CS101"), ("karate", "m1", "m34"),
                        ("airports", "MAA", "LIS")):
            truth = nx.has_path(NX[g], s, t)
            T.append(C(g, {"source": s, "target": t},
                       lambda o, tr=truth: ((1.0 if first_bool(o, ("reachable", "is_reachable", "path_exists")) == tr else 0.0), f"truth {tr}")))
    elif name == "shortest_path_unweighted":
        for g, s, t in (("karate", "m1", "m34"), ("courses", "CS101", "CS401"), ("airports", "MAA", "LIS"),
                        ("airports", "MAA", "SCL"), ("courses", "CS401", "CS101")):
            G = NX[g]
            hops = nx.shortest_path_length(G, s, t) if nx.has_path(G, s, t) else None

            def chk(o, G=G, s=s, t=t, h=hops):
                if h is None:
                    ok = o.get("status") == "error" or first_bool(o, ("reachable", "found", "path_exists")) is False \
                        or not node_ids(o.get("result"))
                    return (1.0 if ok else 0.0), "no path"
                ids = node_ids(o.get("result"))
                path = [i for i in ids if i not in (None,)]
                # take the path list: consecutive edges must exist
                for _, v in walk(o.get("result")):
                    if isinstance(v, list) and v and all(isinstance(x, dict) and "id" in x for x in v):
                        path = [x["id"] for x in v]
                        break
                valid = path and path[0] == s and path[-1] == t and all(G.has_edge(a, b) for a, b in zip(path, path[1:]))
                return (1.0 if valid and len(path) - 1 == h else 0.0), f"hops {h}, got {len(path) - 1}"
            T.append(C(g, {"source": s, "target": t}, chk))
    elif name == "shortest_path_weighted":
        for g, s, t in (("lesmis", "c74", "c01"), ("airports", "MAA", "LIS"), ("airports", "MAA", "SCL"), ("karate", "m1", "m34")):
            d = nx.shortest_path_length(NX[g], s, t, weight="weight")
            T.append(C(g, {"source": s, "target": t},
                       lambda o, d=d: ((1.0 if close(first_num(o, ("distance", "total_weight", "cost", "length", "total_distance", "weight")), d) else 0.0), f"dist {d}")))
    elif name == "hits":
        for g in ("courses", "airports"):
            h, a = nx.hits(NX[g], max_iter=10000, tol=1e-12)
            h_u, a_u = nx.hits(nx.DiGraph(NX[g].edges()), max_iter=10000, tol=1e-12) if g == "airports" else (h, a)

            def chk(o, a=a, a_u=a_u, h=h, h_u=h_u):
                best = 0.0
                note = ""
                for key in ("authority", "authority_score", "score", "hub", "hub_score"):
                    for ref in ((a, a_u) if "auth" in key or key == "score" else (h, h_u)):
                        rows = ranked(o, prefer=(key,))
                        if not rows or rows[0][1] is None:
                            continue
                        sc, nt = ref_rank_check({"result": [{"id": i, "score": s} for i, s in rows]}, ref)
                        if sc > best:
                            best, note = sc, f"{key}: {nt}"
                return best, note
            T.append(C(g, {}, chk))
    elif name == "k_core":
        for g in ("karate", "lesmis"):
            core = nx.core_number(NX[g])
            mx = max(core.values())
            size = sum(1 for v in core.values() if v == mx)
            T.append(C(g, {}, lambda o, mx=mx, size=size: (
                0.5 * (first_num(o, ("max_core_number", "max_core", "k", "selected_k", "degeneracy")) == mx)
                + 0.5 * (first_num(o, ("size", "core_size", "selected_node_count", "num_nodes", "n_nodes", "node_count")) == size
                         or any(len(s) == size for s in registered_sets(o))), f"max core {mx} size {size}")))
        core = nx.core_number(K)
        size2 = sum(1 for v in core.values() if v >= 2)
        T.append(C("karate", {"k": 2}, lambda o, s=size2: ((1.0 if any(len(x) == s for x in registered_sets(o)) or
                                                             first_num(o, ("size", "core_size", "selected_node_count", "num_nodes")) == s else 0.0), f"2-core size {s}")))
    elif name in ("louvain", "label_propagation", "girvan_newman"):
        for g in ("karate", "lesmis"):
            G = NX[g]
            best = max(nxcom.modularity(G, c, weight="weight") for c in
                       [nxcom.louvain_communities(G, weight="weight", seed=s) for s in range(5)])

            def chk(o, G=G, best=best, g=g):
                sets = registered_sets(o, exclude=(g,))
                q = partition_quality(G, sets)
                if q is None:
                    return 0.0, f"communities not a partition ({len(sets)} subgraphs)"
                target = best if name == "louvain" else best * 0.6
                return min(1.0, q / target), f"modularity {q:.4f} (louvain best {best:.4f})"
            T.append(C(g, {}, chk))
        if name == "girvan_newman":
            split = [set(c) for c in next(nxcom.girvan_newman(K))]

            def chk2(o):
                sets = registered_sets(o, exclude=("karate",))
                return (1.0 if sorted(map(sorted, sets)) == sorted(map(sorted, split)) else 0.0), "first split of karate"
            T.append(C("karate", {"num_communities": 2}, chk2))
    elif name == "maximal_cliques":
        for g in ("karate", "lesmis"):
            cl = list(nx.find_cliques(NX[g]))
            n, mx = len(cl), max(map(len, cl))
            T.append(C(g, {}, lambda o, n=n, mx=mx: (
                0.5 * (first_num(o, ("n_maximal", "total_cliques", "maximal_cliques", "num_cliques", "total", "count",
                                     "total_maximal_cliques", "number_of_cliques")) == n)
                + 0.5 * (first_num(o, ("max_size", "clique_number", "size", "largest_size")) == mx), f"{n} cliques, max {mx}")))
    elif name == "minimum_spanning_tree":
        for g in ("karate", "lesmis", "airports"):
            G = NX[g].to_undirected() if NX[g].is_directed() else NX[g]
            w = sum(d["weight"] for *_, d in nx.minimum_spanning_edges(G, data=True))
            T.append(C(g, {}, lambda o, w=w: ((1.0 if close(first_num(o, ("total_weight", "weight", "total_cost", "cost")), w) else 0.0), f"total {w}")))
    elif name == "max_flow_min_cut":
        for g, s, t in (("karate", "m1", "m34"), ("lesmis", "c74", "c26"), ("courses", "CS101", "CS401"), ("airports", "MAA", "LHR")):
            G = NX[g].copy()
            if not G.is_directed():
                G = G.to_directed()
            for u, v, d in G.edges(data=True):
                d["capacity"] = d.get("weight", 1.0)
            f = nx.maximum_flow_value(G, s, t)
            T.append(C(g, {"source": s, "target": t},
                       lambda o, f=f: ((1.0 if close(first_num(o, ("max_flow", "flow_value", "max_flow_value", "value", "flow", "maximum_flow")), f) else 0.0), f"flow {f}")))
    elif name == "motif_count":
        for g in ("karate", "lesmis"):
            tri = sum(nx.triangles(NX[g]).values()) // 3
            T.append(C(g, {}, lambda o, t=tri: ((1.0 if first_num(o, ("triangle_count", "triangles", "triangle", "count")) == t
                                                  or any(v == t for k, v in walk(o.get("result")) if k and "tri" in str(k)) else 0.0), f"triangles {t}")))
    elif name == "greedy_coloring":
        for g in ("karate", "lesmis"):
            n = max(nx.greedy_color(NX[g], strategy="largest_first").values()) + 1
            chi_lb = max(map(len, nx.find_cliques(NX[g])))

            def chk(o, n=n, lb=chi_lb):
                c = first_num(o, ("num_colors", "color_count", "colors_used", "n_colors", "number_of_colors"))
                if c is None:
                    return 0.0, "no colour count"
                return (1.0 if lb <= c <= n else 0.3), f"colours {c} (nx {n}, clique bound {lb})"
            T.append(C(g, {}, chk))
    elif name == "link_prediction":
        G = K
        ref = {frozenset((u, v)): p for u, v, p in nx.adamic_adar_index(G)}

        def chk(o, ref=ref):
            pairs = []
            for _, v in walk(o.get("result")):
                if isinstance(v, list) and v and all(isinstance(x, dict) and "score" in x for x in v):
                    for x in v:
                        ids = [y["id"] for y in x.values() if isinstance(y, dict) and "id" in y]
                        if len(ids) == 2:
                            pairs.append((frozenset(ids), x["score"]))
                    break
            if not pairs:
                return 0.0, "no pairs"
            good = sum(1 for p, s in pairs[:10] if p in ref and close(s, ref[p]))
            best = sorted(ref.values(), reverse=True)[:min(10, len(pairs))]
            order = all(close(pairs[i][1], best[i]) for i in range(len(best)))
            return good / min(10, len(pairs)) * (1 if order else 0.5), f"{good} AA scores match, order {order}"
        T.append(C("karate", {"method": "adamic_adar"}, chk))
    elif name == "node_similarity":
        for g, a, b in (("karate", "m1", "m2"), ("airports", "JFK", "LAX")):
            G = NX[g].to_undirected()
            na, nb = set(G.neighbors(a)), set(G.neighbors(b))
            j = len(na & nb) / len(na | nb)
            T.append(C(g, {"source": a, "target": b},
                       lambda o, j=j, c=len(na & nb): (0.7 * any_num_close(o, j) + 0.3 * any_num_close(o, c), f"jaccard {j:.6f} common {c}")))
    elif name == "node_embedding_similarity":
        for g, n in (("karate", "m1"), ("airports", "MAA")):
            G = NX[g].to_undirected()
            nbrs = set(G.neighbors(n))

            def chk(o, nbrs=nbrs, n=n):
                rows = ranked(o)
                if not rows:
                    return 0.0, "no ranked list"
                top = [r[0] for r in rows[:10] if r[0] != n]
                frac = sum(1 for x in top if x in nbrs) / max(1, len(top))
                return min(1.0, 0.4 + frac), f"{frac:.0%} of top 10 are neighbours"
            T.append(C(g, {"node": n}, chk))
    elif name == "topological_sort":
        G = CO

        def chk(o, G=G):
            for _, v in walk(o.get("result")):
                if isinstance(v, list) and len(v) == G.number_of_nodes() and all(isinstance(x, dict) and "id" in x for x in v):
                    pos = {x["id"]: i for i, x in enumerate(v)}
                    ok = all(pos[u] < pos[w] for u, w in G.edges())
                    return (1.0 if ok else 0.0), "valid order" if ok else "order violates an edge"
            return 0.0, "no full order"
        T.append(C("courses", {}, chk))
        T.append(C("karate", {}, lambda o: ((1.0 if o.get("status") == "error" or first_bool(o, ("is_dag",)) is False else 0.0), "undirected / cyclic")))
    return T


# ------------------------------------------------------------------ driver
USEFUL_OPTIONS = {"node", "direction", "mode", "weighted", "use_weights", "num_communities", "k", "method",
                  "target", "seeds", "resolution", "normalized", "score", "sort_by", "rank_by", "score_type"}


def run_impl(tool, schema, tc):
    args = adapt(schema, tc["args"])
    if args is None:
        return None, "unsupported arguments", 0.0
    t0 = time.time()
    out = tool.call(STORE, **args)
    dt = time.time() - t0
    return out, args, dt


def evaluate(raw: Path):
    report = {}
    for tdir in sorted(p for p in raw.iterdir() if p.is_dir()):
        name = tdir.name
        tests = tests_for(name)
        impls = {}
        for idir in sorted(p for p in tdir.iterdir() if p.is_dir()):
            rep = validate(idir)
            entry = {"path": str(idir), "validator_errors": rep.errors, "cases": [], "score": 0.0, "max_time": 0.0}
            if rep.errors:
                impls[idir.name] = entry
                continue
            tool = load_tool(idir)
            schema = tool.manifest["parameters"].get("properties", {})
            total, n = 0.0, 0
            for tc in tests:
                out, args, dt = run_impl(tool, schema, tc)
                entry["max_time"] = max(entry["max_time"], dt)
                if out is None:
                    entry["cases"].append({"case": tc["label"], "score": 0.0, "note": args})
                    n += 1
                    continue
                if out.get("status") != "ok" and "error" not in tc["label"]:
                    try:
                        sc, note = tc["check"](out)
                    except Exception as exc:  # noqa: BLE001
                        sc, note = 0.0, f"check failed: {exc}"
                    if sc == 0:
                        note = f"tool error: {str(out.get('error'))[:150]}"
                else:
                    try:
                        sc, note = tc["check"](out)
                    except Exception as exc:  # noqa: BLE001
                        sc, note = 0.0, f"check crashed: {type(exc).__name__}: {exc}"
                if dt > 30:
                    sc, note = 0.0, f"too slow ({dt:.1f}s)"
                sc = float(sc)
                entry["cases"].append({"case": tc["label"], "args": args, "score": round(sc, 3), "note": note, "time": round(dt, 3)})
                total += sc
                n += 1
            # determinism
            if tests:
                tc = tests[0]
                o1, _, _ = run_impl(tool, schema, tc)
                o2, _, _ = run_impl(tool, schema, tc)
                entry["deterministic"] = bool(o1 is not None and o2 is not None and
                                              _strip_ids(o1) == _strip_ids(o2))
            entry["score"] = round(total / n, 4) if n else 0.0
            entry["options"] = sorted(set(schema) & USEFUL_OPTIONS)
            entry["desc_len"] = len(tool.manifest.get("description", ""))
            impls[idir.name] = entry
            print(f"{name:32s} {idir.name}  score={entry['score']:.3f}  t={entry['max_time']:.2f}s  opts={entry['options']}", flush=True)
        # timings are noisy, so only "slow" (> 5 s) counts; the rest of the key is stable across runs
        ranking = sorted(impls, key=lambda i: (-impls[i]["score"], not impls[i].get("deterministic", False),
                                               impls[i]["max_time"] > 5, -len(impls[i].get("options", [])),
                                               -impls[i].get("desc_len", 0), i))
        report[name] = {"winner": ranking[0], "ranking": ranking, "implementations": impls}
    return report


def _strip_ids(o):
    """Output with subgraph ids removed (they change on every call)."""
    s = json.dumps(o, sort_keys=True)
    return re.sub(r'"[a-z]+~\d+"', '"~"', s)


def write_markdown(report, path: Path):
    lines = ["# Tool curation report", "",
             "Every implementation was run on test cases from the provided datasets and compared with NetworkX.",
             "Score = mean over test cases (1 = matches the reference). Ties broken by determinism, speed, options, description.", "",
             "| Tool | Chosen | Score | Max time (s) | Runner-up scores |", "| --- | --- | --- | --- | --- |"]
    for name, r in report.items():
        w = r["implementations"][r["winner"]]
        others = ", ".join(f"{i}:{r['implementations'][i]['score']:.2f}" for i in r["ranking"][1:])
        lines.append(f"| {name} | {r['winner']} | {w['score']:.3f} | {w['max_time']:.2f} | {others} |")
    lines += ["", "## Details", ""]
    for name, r in report.items():
        lines.append(f"### {name}")
        for i in r["ranking"]:
            e = r["implementations"][i]
            lines.append(f"- **{i}** score {e['score']:.3f}, max {e['max_time']:.2f}s, deterministic {e.get('deterministic')}, options {e.get('options')}")
            for c in e["cases"]:
                if c["score"] < 1:
                    lines.append(f"  - {c['case']}: {c['score']} ({c['note']})")
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def install(report, dest: Path):
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    for name, r in report.items():
        src = Path(r["implementations"][r["winner"]]["path"])
        shutil.copytree(src, dest / name / src.name, ignore=shutil.ignore_patterns("__pycache__", "tests"))
    print(f"Installed {len(report)} tools into {dest}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", default=str(ROOT.parent / "tools"), help="folder with the full class registry")
    ap.add_argument("--only", nargs="*", help="only these tool names")
    ap.add_argument("--install", action="store_true", help="copy the winners into registry/tools/")
    args = ap.parse_args()
    raw = Path(args.raw)
    if args.only:
        tmp = {n: raw / n for n in args.only}
        report = {}
        for n, p in tmp.items():
            sub = evaluate_one(p)
            report.update(sub)
    else:
        report = evaluate(raw)
    out_json = ROOT / "curation" / ("report.json" if not args.only else "report_partial.json")
    out_json.write_text(json.dumps(report, indent=1, default=str), encoding="utf-8")
    write_markdown(report, out_json.with_suffix(".md"))
    if args.install and not args.only:
        install(report, ROOT / "registry" / "tools")


def evaluate_one(tool_dir: Path):
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        link = Path(td) / tool_dir.name
        shutil.copytree(tool_dir, link)
        rep = evaluate(Path(td))
        for r in rep.values():
            for i, e in r["implementations"].items():
                e["path"] = str(tool_dir / i)
        return rep


if __name__ == "__main__":
    main()
