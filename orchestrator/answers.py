"""Turning a final_answer call into the answers.json entry, and checking that the trace supports it."""
from __future__ import annotations

import math

from graphkit import GraphStore

from .prompts import ANSWER_TYPES, STATUSES


def _walk(obj):
    yield obj
    if isinstance(obj, dict):
        for v in obj.values():
            yield from _walk(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _walk(v)


def evidence(tool_outputs: list[dict]) -> tuple[set[str], list[float]]:
    """Every string and number that appeared in a successful tool output."""
    strings, numbers = set(), []
    for out in tool_outputs:
        if out.get("status") != "ok":
            continue
        for v in _walk(out):
            if isinstance(v, str):
                strings.add(v)
            elif isinstance(v, (int, float)) and not isinstance(v, bool):
                numbers.append(float(v))
    return strings, numbers


def build_answer(args: dict) -> tuple[dict | None, str | None]:
    """(answer dict, None) or (None, problem) for a final_answer call's arguments."""
    status = args.get("status")
    if status is None and any(args.get(k) is not None for k in ("number", "boolean", "nodes")):
        # some models drop the field when the answer is obvious; a typed value means answered
        status = args["status"] = "answered"
    if status not in STATUSES:
        return None, f"status must be one of {STATUSES}."
    atype = args.get("answer_type") or "text"
    if atype not in ANSWER_TYPES:
        return None, f"answer_type must be one of {ANSWER_TYPES}."
    if status != "answered":
        return {"type": "text", "value": args.get("text") or args.get("answer_text") or ""}, None
    nodes = args.get("nodes")
    if isinstance(nodes, str):
        nodes = [n.strip() for n in nodes.split(",") if n.strip()]
    if atype == "number":
        value = args.get("number")
        if isinstance(value, str):
            try:
                value = float(value)
            except ValueError:
                value = None
        if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value):
            return None, "answer_type is number, so fill the 'number' field with the value."
        if isinstance(value, float) and value.is_integer() and abs(value) < 1e15:
            value = int(value)
        return {"type": "number", "value": value}, None
    if atype == "boolean":
        value = args.get("boolean")
        if isinstance(value, str) and value.lower() in ("true", "false"):
            value = value.lower() == "true"
        if not isinstance(value, bool):
            return None, "answer_type is boolean, so fill the 'boolean' field with true or false."
        return {"type": "boolean", "value": value}, None
    if atype in ("node", "node_list", "path"):
        if not nodes or not all(isinstance(n, str) for n in nodes):
            return None, f"answer_type is {atype}, so list the node ids in the 'nodes' field."
        if atype == "node":
            if len(nodes) != 1:
                return None, "answer_type node takes exactly one node id; use node_list for several."
            return {"type": "node", "value": nodes[0]}, None
        return {"type": atype, "value": list(nodes)}, None
    return {"type": "text", "value": args.get("text") or args.get("answer_text") or ""}, None


def grounding_problems(answer: dict, status: str, tool_outputs: list[dict], store: GraphStore) -> list[str]:
    """Reasons the trace may not support an 'answered' answer (empty list = fine)."""
    if status != "answered":
        return []
    ok_outputs = [o for o in tool_outputs if o.get("status") == "ok"]
    if not ok_outputs:
        return ["You answered without any successful tool result. Every fact must come from a tool: call the tool "
                "that computes it, or use status unsupported/clarification_needed."]
    strings, numbers = evidence(ok_outputs)
    problems = []
    atype, value = answer["type"], answer["value"]
    if atype in ("node", "node_list", "path"):
        nodes = [value] if atype == "node" else value
        known = {n for g in store.list_graphs() for n in store.get(g["graph_id"]).nodes()}
        missing = [n for n in nodes if n not in strings]
        not_ids = [n for n in nodes if n not in known]
        if not_ids:
            problems.append(f"{not_ids} are not node ids. Use the ids from the tool outputs (e.g. 'm34', 'MAA'), not labels.")
        elif missing:
            problems.append(f"Node(s) {missing} do not appear in any tool output. Only return nodes the tools returned.")
    elif atype == "number":
        if not any(math.isclose(value, n, rel_tol=1e-6, abs_tol=1e-9) for n in numbers):
            problems.append(f"The number {value} does not appear in any tool output. If you computed it from tool "
                            f"values, call final_answer again unchanged to confirm; otherwise use the exact tool value.")
    return problems
