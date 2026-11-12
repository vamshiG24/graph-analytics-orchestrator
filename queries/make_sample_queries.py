"""Build queries/sample_queries.json: our own practice questions with expected answers.

    python queries/make_sample_queries.py

Expected values come from NetworkX where the answer does not depend on an implementation
choice, and from the curated tools for chained questions whose answer depends on, e.g., the
communities Louvain finds. The public set from the instructors replaces this file for grading.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import networkx as nx  # noqa: E402

from graphkit import GraphStore  # noqa: E402
from graphkit.testing import to_networkx  # noqa: E402
from orchestrator.registry import Registry  # noqa: E402

store = GraphStore()
reg = Registry.load()
G = {g: to_networkx(store.get(g)) for g in ("karate", "lesmis", "airports", "courses", "projects")}


def tool(name, **args):
    out = reg.call(store, name, reg.prepare(name, args))  # same conventions as the orchestrator
    assert out["status"] == "ok", out
    return out


def top(scores, k):
    return sorted(scores, key=lambda n: (-scores[n], n))[:k]


def largest_community(graph_id):
    out = tool("louvain", graph_id=graph_id, top_k=100)
    gids = [v for v in _walk(out) if isinstance(v, str) and "~" in v and store.has_graph(v)]
    return max(gids, key=lambda g: store.get(g).number_of_nodes())


def _walk(o):
    yield o
    if isinstance(o, dict):
        for v in o.values():
            yield from _walk(v)
    elif isinstance(o, list):
        for v in o:
            yield from _walk(v)


def ans(kind, atype=None, value=None, status="answered", ordered=False):
    exp = {"status": status}
    if status == "answered":
        exp["answer"] = {"type": atype, "value": value}
        if ordered:
            exp["ordered"] = True
    return kind, exp


Q = []


def add(question, kind_exp):
    kind, exp = kind_exp
    Q.append({"query_id": f"s{len(Q) + 1:02d}", "question": question, "kind": kind, "expected": exp})


A, K, L, C, P = G["airports"], G["karate"], G["lesmis"], G["courses"], G["projects"]

# single tool
add("How many members are in the karate club network?", ans("single", "number", K.number_of_nodes()))
pr = nx.pagerank(A, weight=None)  # centralities are unweighted by convention
add("Which airport has the highest PageRank in the airline route network?", ans("single", "node", top(pr, 1)[0]))
pr = nx.pagerank(L, weight=None)
add("List the three most influential characters in Les Miserables by PageRank, most influential first.",
    ans("single", "node_list", top(pr, 3), ordered=True))
add("How many airports can you fly to non-stop from Chennai?", ans("single", "number", A.out_degree("MAA")))
add("What is the minimum number of flights needed to get from Chennai to Lisbon?",
    ans("single", "number", nx.shortest_path_length(A, "MAA", "LIS")))
add("What is the shortest total flying distance in km from Chennai to Lisbon using the route network?",
    ans("single", "number", nx.shortest_path_length(A, "MAA", "LIS", weight="weight")))
add("Is the student-project graph bipartite?", ans("single", "boolean", nx.is_bipartite(P)))
bc = nx.betweenness_centrality(K)
add("Which karate club member lies on the most shortest paths between other members?", ans("single", "node", top(bc, 1)[0]))
add("How many triangles are there in the karate club friendship network?", ans("single", "number", sum(nx.triangles(K).values()) // 3))
add("Following prerequisite links, can you get from Distributed Systems back to Programming Basics?",
    ans("single", "boolean", nx.has_path(C, "CS401", "CS101")))
add("How many connected components does the student-project graph have?", ans("single", "number", nx.number_connected_components(P)))
add("What is the largest number of students that can each be assigned a different project they are willing to work on?",
    ans("single", "number", len(nx.bipartite.maximum_matching(P, top_nodes=[n for n in P if n.startswith("S")])) // 2))
add("What is the diameter of the karate club network?", ans("single", "number", nx.diameter(K)))
Gd = K.to_directed()
nx.set_edge_attributes(Gd, 1.0, "capacity")
add("What is the maximum flow between the instructor (member 1) and the administrator (member 34) in the karate club, with every friendship having capacity 1?",
    ans("single", "number", nx.maximum_flow_value(Gd, "m1", "m34")))
add("What is Valjean's clustering coefficient?", ans("single", "number", round(nx.clustering(L, "c74"), 6)))
add("Which character in Les Miserables has the most co-appearance partners?", ans("single", "node", max(L.degree, key=lambda x: x[1])[0]))

# multi-step
big = largest_community("karate")
spr = tool("pagerank", graph_id=big, top_k=1)["result"][0]["id"]
add("Who is the most influential member, by PageRank, of the largest Louvain community in the karate club?", ans("multi", "node", spr))
big = largest_community("lesmis")
sbc = tool("betweenness_centrality", graph_id=big, top_k=1)["result"][0]["id"]
add("In the largest community that Louvain finds in Les Miserables, which character has the highest betweenness centrality?",
    ans("multi", "node", sbc))
india = [n for n, d in A.nodes(data=True) if d["country"] == "India"]
add("How many airports in India are in the network?", ans("multi", "number", len(india)))
sub_ids = tool("filter_nodes", graph_id="airports", attribute="country", value="India")["result_graph_id"]
deg = tool("degree_centrality", graph_id=sub_ids, top_k=1)["result"][0]["id"]
add("Considering only the routes between airports in India, which Indian airport has the most connections?", ans("multi", "node", deg))
lev = [n for n, d in C.nodes(data=True) if d["level"] == 300]
add("How many 300-level courses are there, counted from the course catalogue?", ans("multi", "number", len(lev)))
add("How many more non-stop destinations does Delhi have than Chennai?", ans("multi", "number", A.out_degree("DEL") - A.out_degree("MAA")))

# ambiguous
add("Which node is the most central?", ans("ambiguous", status="clarification_needed"))
add("How far is Chennai from Delhi?", ans("ambiguous", status="clarification_needed"))
add("How many nodes does the graph have?", ans("ambiguous", status="clarification_needed"))

# unsupported
add("What is the cheapest ticket price from Chennai to Delhi?", ans("unsupported", status="unsupported"))
add("What is the eigenvector centrality of member 1 in the karate club?", ans("unsupported", status="unsupported"))
add("Which airline flies the most routes out of Frankfurt?", ans("unsupported", status="unsupported"))
add("Does the karate club network contain a Hamiltonian cycle?", ans("unsupported", status="unsupported"))

out = ROOT / "queries" / "sample_queries.json"
out.write_text(json.dumps(Q, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"Wrote {len(Q)} queries to {out}")
for q in Q:
    print(q["query_id"], q["kind"], json.dumps(q["expected"]), q["question"][:60])
