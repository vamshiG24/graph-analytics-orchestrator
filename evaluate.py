"""Score answers.json against a query file that has expected answers.

    python evaluate.py --answers answers.json --expected queries/sample_queries.json

Expected entries look like the public set: {"query_id", "question", "expected": {"status", "answer"}}
(also accepted: "expected_status"/"expected_answer" at the top level). Rules follow the handout:
numbers within 0.1%, node lists as sets (or in order when "ordered": true), ambiguous and
unsupported questions only need the right status.
"""
from __future__ import annotations

import argparse
import json
import math
from collections import Counter
from pathlib import Path


def expected_of(q: dict) -> tuple[str, dict | None, bool]:
    exp = q.get("expected") or {}
    status = exp.get("status") or q.get("expected_status") or "answered"
    answer = exp.get("answer") or q.get("expected_answer")
    ordered = bool(exp.get("ordered", q.get("ordered", False)))
    return status, answer, ordered


def valid_topological_order(order, graph_id: str) -> tuple[bool, str]:
    """Any order that lists every node once with each prerequisite before its course."""
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from graphkit import GraphStore
    g = GraphStore().get(graph_id)
    if not isinstance(order, list) or sorted(order) != sorted(g.nodes()):
        return False, f"not a full ordering of the {g.number_of_nodes()} nodes"
    pos = {n: i for i, n in enumerate(order)}
    bad = [(u, v) for u, v, _ in g.edges() if pos[u] > pos[v]]
    return not bad, "valid order" if not bad else f"violates {bad[:3]}"


def compare(got: dict | None, want: dict | None, ordered: bool, check: str | None = None,
            graph_id: str | None = None) -> tuple[bool, str]:
    if want is None:
        return True, "no expected value"
    if not got:
        return False, "no answer"
    if check == "topological_order":
        return valid_topological_order(got.get("value"), graph_id)
    wt, wv, gt, gv = want.get("type"), want.get("value"), got.get("type"), got.get("value")
    if wt == "number":
        if isinstance(gv, bool) or not isinstance(gv, (int, float)):
            return False, f"expected number {wv}, got {gt} {gv}"
        ok = math.isclose(gv, wv, rel_tol=1e-3, abs_tol=1e-9)
        return ok, f"{gv} vs {wv}"
    if wt == "boolean":
        return gv is wv, f"{gv} vs {wv}"
    if wt == "node":
        if gt == "node_list" and isinstance(gv, list) and len(gv) == 1:
            gv = gv[0]
        return gv == wv, f"{gv} vs {wv}"
    if wt in ("node_list", "path"):
        if not isinstance(gv, list):
            gv = [gv]
        if wt == "path" or ordered:
            return list(gv) == list(wv), f"{gv} vs {wv}"
        return set(gv) == set(wv), f"{sorted(gv)} vs {sorted(wv)}"
    if wt == "text":
        return str(gv).strip().lower() == str(wv).strip().lower(), "text (check by hand)"
    return False, f"unknown expected type {wt}"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--answers", default="answers.json")
    ap.add_argument("--expected", required=True)
    ap.add_argument("--report", help="optional markdown report path")
    args = ap.parse_args()

    data = json.loads(Path(args.expected).read_text(encoding="utf-8-sig"))
    queries = data.get("queries", data) if isinstance(data, dict) else data
    answers = {a["query_id"]: a for a in json.loads(Path(args.answers).read_text(encoding="utf-8"))}

    rows, by_kind = [], Counter()
    correct = Counter()
    for q in queries:
        qid = str(q.get("query_id") or q.get("id"))
        status, want, ordered = expected_of(q)
        kind = q.get("kind") or q.get("category") or status
        got = answers.get(qid)
        if got is None:
            ok, note = False, "not answered"
        elif got["status"] != status:
            ok, note = False, f"status {got['status']} (expected {status})"
        elif status != "answered":
            ok, note = True, "right status"
        else:
            ok, note = compare(got.get("answer"), want, ordered, (q.get("expected") or {}).get("check"), q.get("graph"))
        by_kind[kind] += 1
        correct[kind] += ok
        rows.append((qid, kind, ok, note, q.get("question", "")))

    total = sum(by_kind.values())
    lines = [f"# Evaluation: {sum(correct.values())}/{total} correct ({100 * sum(correct.values()) / max(1, total):.1f}%)", "",
             "| Kind | Correct |", "| --- | --- |"]
    lines += [f"| {k} | {correct[k]}/{n} |" for k, n in sorted(by_kind.items())]
    lines += ["", "| Query | Kind | OK | Note | Question |", "| --- | --- | --- | --- | --- |"]
    lines += [f"| {qid} | {kind} | {'yes' if ok else 'NO'} | {note} | {question} |" for qid, kind, ok, note, question in rows]
    text = "\n".join(lines)
    print(text)
    if args.report:
        Path(args.report).write_text(text + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
