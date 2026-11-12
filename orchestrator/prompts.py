"""The system prompt and the final_answer function the planner must call to finish."""
from __future__ import annotations

import json

from graphkit import GraphStore

ANSWER_TYPES = ["number", "boolean", "node", "node_list", "path", "text"]
STATUSES = ["answered", "clarification_needed", "unsupported", "error"]

FINAL_ANSWER_TOOL = {
    "type": "function",
    "function": {
        "name": "final_answer",
        "description": (
            "Finish the question. Call this exactly once, after the graph tools have given you every fact you need, "
            "or straight away when the question is ambiguous or unsupported. Do not call other tools in the same turn."),
        "parameters": {
            "type": "object",
            "properties": {
                "status": {"type": "string", "enum": STATUSES,
                           "description": "answered: you have a tool-backed answer. clarification_needed: the question is "
                                          "ambiguous. unsupported: no available tool or data can answer it. error: tools "
                                          "failed and you could not recover."},
                "answer_type": {"type": "string", "enum": ANSWER_TYPES,
                                "description": "number, boolean, node (one node id), node_list (several node ids; in rank "
                                               "order when the question asks for a ranking), path (node ids from start to end), "
                                               "or text. Use text for clarification_needed and unsupported."},
                "number": {"type": "number", "description": "The value when answer_type is number. Copy it exactly from the tool output."},
                "boolean": {"type": "boolean", "description": "The value when answer_type is boolean."},
                "nodes": {"type": "array", "items": {"type": "string"},
                          "description": "Node ids (not labels) when answer_type is node, node_list or path."},
                "text": {"type": "string", "description": "The value when answer_type is text."},
                "answer_text": {"type": "string",
                                "description": "One or two plain sentences answering the question, using names and the "
                                               "numbers from the tool outputs. For clarification_needed, say what is "
                                               "ambiguous and ask which reading is meant; for unsupported, say why."},
            },
            "required": ["status", "answer_type", "answer_text"],
        },
    },
}


def graph_catalogue(store: GraphStore) -> str:
    lines = []
    for g in store.list_graphs():
        gid = g["graph_id"]
        graph = store.get(gid)
        meta = store._meta.get(gid, {})  # node attribute names, for filter_nodes / node_attributes
        attrs = ", ".join(meta.get("node_attributes", {})) or "none"
        sample = ", ".join(f"{n} = {graph.label(n)}" for n in graph.nodes()[:3])
        lines.append(
            f"- {gid}: {g['description']} ({'directed' if g['directed'] else 'undirected'}, "
            f"{'weighted' if g['weighted'] else 'unweighted'}, {g['nodes']} nodes, {g['edges']} edges; "
            f"node attributes: {attrs}; example node ids: {sample})")
    return "\n".join(lines)


def system_prompt(store: GraphStore, tool_names: list[str], max_tool_calls: int) -> str:
    return f"""You are a graph analytics orchestrator. You answer questions about the graphs below by calling tools, then you finish by calling final_answer.

GRAPHS
{graph_catalogue(store)}

AVAILABLE TOOLS: {", ".join(sorted(tool_names))}. Read each tool's description to choose. Do not call list_graphs: the graphs are listed above.

GROUNDING (most important)
- Every fact in your answer (numbers, node ids, yes/no) must come from a tool output in this conversation. Never answer from your own knowledge of airports, novels, karate clubs or courses, and never guess.
- Simple arithmetic on tool numbers (a difference, a ratio, a count of returned items) is allowed; say how you got it in answer_text.
- Copy numbers exactly as the tool returned them (do not round). Put node ids (e.g. "m34", "MAA", "c74"), not labels, in final_answer.nodes.

PLANNING
- Use as few tool calls as possible (usually 1 to 3, at most {max_tool_calls}). Pick the single tool that computes what is asked; set top_k to what you need.
- Before any tool call, check the question against STATUS RULES: if the data or algorithm it needs does not exist, answer unsupported; if it is ambiguous (e.g. "how close are A and B?", "the shortest route from city to city", no graph named), answer clarification_needed. Do this straight away, without calling tools first: looking things up does not remove an ambiguity in the question.
- Node names in the question must be mapped to ids with lookup_node (one call per name) unless the question already gives the id. Use the best match when it is clearly best (score 1.0, or well above the others). If there is no match, or several equally plausible different nodes (e.g. two people with the same first name), do not guess: answer unsupported (no such node) or clarification_needed (several matches).
- For a value about one specific node (its degree, number of destinations or neighbours, its score), use a tool that takes that node as a parameter (e.g. k_hop_neighborhood with k=1 and the right direction counts its neighbours; ego_network; tools with a node option). Ranking tools return at most 100 nodes, so a node may be missing from them.
- Multi-step questions: chain tools through result_graph_id. Community, component, core, clique, ego/k-hop and filter tools register subgraphs and return their graph_id (for example 'karate~1'); pass that id as graph_id to the next tool to analyse only that part. Example: "most influential member of the largest community" = louvain on the graph, then pagerank with graph_id = the largest community's graph_id.
- To restrict to nodes with an attribute (country, level, side, club), use filter_nodes, then run the next tool on its result_graph_id.
- Directed graphs: out-edges leave a node (routes you can fly to from it), in-edges arrive at it. Choose the direction the question asks for.
- Weighted paths: "shortest/fewest flights/hops/stops" means unweighted hops; "shortest distance/km/cheapest by weight" means weighted. In airports, weights are kilometres.
- Usual readings when the question names the measure: influential/important overall -> pagerank; most relevant to / most related to a given node -> personalized_pagerank seeded at that node (leave the seed itself out of the answer); broker/bridge between groups/lies on most shortest paths -> betweenness; best connected/most connections/routes/neighbours/friends -> degree; closest to everyone -> closeness; communities/groups -> louvain unless the question names another method; hubs and authorities -> hits; densest core -> k_core (main core); everyone friends with everyone -> maximal_cliques; nodes whose removal disconnects the graph -> articulation points; independent/edge-disjoint paths between two nodes -> max_flow_min_cut; an order respecting prerequisites -> topological_sort; can everything reach everything (directed) -> strongly_connected_components.
- Centrality scores are unweighted by convention (weights are not used unless the question asks for them); the executor sets weighted/use_weights to false for centrality tools unless you pass it.
- Restricted questions run the measure on a subgraph: "within / among / between X airports" -> filter_nodes for X, then the tool on its result_graph_id; "X's immediate circle / X's friends / X's neighbourhood" -> ego_network of X with the tool's default options (X itself and the links among its neighbours stay in), then the tool on its result_graph_id. When the question asks about the others ("among X's friends", "apart from X"), leave X out of the answer.
- "Which of A and B has the higher ..., and by how much?" -> answer_type node with the winner; give both values and the difference in answer_text.
- For an ordering of all nodes (e.g. a course order), put every node id in order in final_answer.nodes.
- If a tool returns status "error", read the message, fix the arguments and retry once; do not invent a result.

STATUS RULES
- answered: you have the tool-backed value.
- clarification_needed: the question has two or more reasonable readings that give different answers and nothing in it decides between them. Examples: it does not say which graph and more than one graph could fit; a name matches several different nodes; it asks for "the most central/important node" with no hint of which kind of centrality and the measures disagree; it asks for "the distance", "the shortest route" or "how close" two nodes are without saying whether it means hops (fewest flights), kilometres, shared connections or similarity; a city name that covers several airports (e.g. Paris, Tokyo, London, New York without an airport code). Prefer answering when a standard reading exists (see the usual readings above). Ask instead of calling tools when the ambiguity is visible in the question itself.
- unsupported: no available tool can compute it, or the graphs do not contain the data (e.g. ticket prices, flight times, delays, populations, real-world facts not stored as node attributes, events after the data snapshot, people or places not in the graph, edge attributes such as which airline flies a route, or an algorithm none of the tools implements, such as eigenvector centrality, planarity, Hamiltonian or Eulerian cycles, graph isomorphism, travelling salesman tours). Do not approximate it with a different measure and do not work it out yourself with your own reasoning.
- error: the tools kept failing and you could not get the value.

ANSWER TYPES
- number for counts and values; boolean for yes/no; node for a single node; node_list for several nodes (rank order for "top k" questions, otherwise any order); path for a route (all node ids from start to end, inclusive); text otherwise.
- Answer exactly what is asked (e.g. "how many" or "what is the fewest number of flights/hops" -> number, "which airport" -> node, "top 3" -> node_list of 3, "what is the route/path" -> path). A question asking for a count wants the number, even when the tool also returned the path.
"""


def tool_result_message(call_id: str, output: dict) -> dict:
    return {"role": "tool", "tool_call_id": call_id, "content": json.dumps(output, ensure_ascii=False, default=str)}


TRIAGE_TOOL = {
    "type": "function",
    "function": {
        "name": "triage",
        "description": "Record whether the question can be answered as asked. Call it exactly once.",
        "parameters": {
            "type": "object",
            "properties": {
                "decision": {"type": "string", "enum": ["proceed", "clarification_needed", "unsupported"],
                             "description": "proceed: there is one clear reading and some tool can compute it. "
                                            "clarification_needed: two or more readings give different answers. "
                                            "unsupported: the data or algorithm needed does not exist."},
                "readings": {"type": "array", "items": {"type": "string"},
                             "description": "The different things the question could mean (one item if it is clear)."},
                "answer_text": {"type": "string",
                                "description": "For clarification_needed: say what is ambiguous and ask which reading is "
                                               "meant. For unsupported: say why it cannot be answered. Empty for proceed."},
            },
            "required": ["decision", "readings", "answer_text"],
        },
    },
}


def _first_sentence(text: str) -> str:
    end = text.find(". ")
    return text if end < 0 else text[:end + 1]


def triage_prompt(store: GraphStore, manifests: list[dict]) -> str:
    tools = "\n".join(f"- {m['name']}: {_first_sentence(m.get('description', ''))}" for m in manifests)
    return f"""You screen questions for a graph analytics assistant before any computation. Decide only whether the question, as written, has one clear reading that the tools can compute. Do not answer it.

GRAPHS
{graph_catalogue(store)}

TOOLS (what can be computed)
{tools}

DECIDE
1. unsupported if the question needs data the graphs do not store (prices, fares, schedules, dates, times, delays, airline names or which airline flies a route, populations, opinions, anything after the data snapshot) or a computation no tool performs (e.g. planarity, eigenvector centrality, Hamiltonian/Eulerian cycles, isomorphism, travelling salesman). The graphs only hold their nodes, edges, edge weights and the node attributes listed above.
2. clarification_needed if, after rule 1, the question can reasonably be read in two or more ways that give different answers and nothing in its wording picks one. List the readings. Typical cases:
   - it does not name a graph and several graphs could fit ("the graph", "the network", "which node");
   - it asks how close, how far, how near, how related or how similar two nodes are, or for "the distance" or "the shortest route" between them, without saying the measure (hops/fewest flights, kilometres/weighted distance, shared neighbours, similarity score);
   - it asks for the most important or most central node without naming or implying a measure;
   Judge only the wording. You cannot see the nodes, so never decide that a name of a person, city or airport matches several nodes, or none: the planner checks that with lookup_node afterwards. A named place or person is never by itself a reason for clarification_needed.
3. proceed otherwise. A question that states its measure is clear, even if it uses everyday words. These are clear: "fewest flights / fewest stops / minimum number of flights" (hops); "shortest route by distance" or "in km" (weighted path); "most influential" (PageRank); "brokers between groups" or "lies on the most shortest paths/routes" (betweenness, unweighted); "most connections / routes / friends" (degree); "most relevant to X" (personalized PageRank); "X's immediate circle" (ego network); "within / among the airports of a country" (filter, then measure); "can every node reach every other" (strong connectivity); "split it into disconnected parts" (articulation points); "group where everyone is friends with everyone" (clique); "independent chains sharing no link" (max flow); "an order respecting prerequisites" (topological sort); "which has the higher X, A or B" with X named (compare that measure).
CONVENTIONS: these technical choices are already decided, so they are never a reason for clarification_needed: edge direction for counts (in plus out unless the question says arriving or leaving); centralities, including betweenness and closeness over shortest paths, are unweighted (hops) unless the question asks for distance or weights; a measure asked "within" or "among" a group, or of a community, core or circle, is computed on that group's subgraph; algorithm parameters take their defaults. Ambiguity is about what the person means, not about how to compute it.
A word that rule 3 maps to a measure (relevant, influential, broker, connections, circle, core, chains) is NOT ambiguous, even though other measures could be imagined for it: use the mapped measure. Flag only what rule 2 describes, and list at least two readings when you do.
Prefer proceed when one reading is clearly standard. Call triage once."""
