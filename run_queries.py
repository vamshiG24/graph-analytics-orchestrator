"""Answer a file of graph questions and write answers.json plus one trace per question.

    python run_queries.py --queries queries/public.json --out answers.json

The API key is read from the LLM_API_KEY environment variable (or a .env file); see README.md.
Traces go to traces/<query_id>.jsonl next to the --out file.

Accepted query files: a JSON list (or {"queries": [...]}) of objects with "query_id"/"id" and
"question"/"query"/"text"; JSON Lines with the same objects; or plain text, one question per line.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from orchestrator.agent import MAX_LLM_CALLS, MAX_TOOL_CALLS, Orchestrator  # noqa: E402
from orchestrator.llm_client import LLM, QuotaExhausted, triage_llm  # noqa: E402
from orchestrator.registry import Registry  # noqa: E402


def load_queries(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8-sig").strip()
    items = None
    try:
        data = json.loads(text)
        items = data.get("queries", data.get("questions")) if isinstance(data, dict) else data
    except json.JSONDecodeError:
        try:
            items = [json.loads(line) for line in text.splitlines() if line.strip()]
        except json.JSONDecodeError:
            items = [line.strip() for line in text.splitlines() if line.strip() and not line.startswith("#")]
    queries = []
    for i, item in enumerate(items, 1):
        if isinstance(item, str):
            item = {"question": item}
        qid = item.get("query_id") or item.get("id") or f"q{i:02d}"
        question = item.get("question") or item.get("query") or item.get("text")
        if not question:
            raise ValueError(f"Query {qid} in {path} has no question text.")
        queries.append({"query_id": str(qid), "question": question})
    return queries


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--queries", required=True, help="file with the questions")
    ap.add_argument("--out", default="answers.json", help="where to write the answers (default answers.json)")
    ap.add_argument("--only", nargs="*", help="answer only these query ids (handy for free-tier quotas)")
    ap.add_argument("--no-cache", action="store_true", help="do not reuse cached LLM responses")
    ap.add_argument("--delay", type=float, default=0.0, help="seconds to wait between questions (rate limits)")
    ap.add_argument("--max-tool-calls", type=int, default=MAX_TOOL_CALLS)
    ap.add_argument("--max-llm-calls", type=int, default=MAX_LLM_CALLS)
    ap.add_argument("--no-triage", action="store_true", help="skip the ambiguity/support check before planning")
    args = ap.parse_args()

    queries = load_queries(Path(args.queries))
    if args.only:
        queries = [q for q in queries if q["query_id"] in set(args.only)]
    out_path = Path(args.out)
    trace_dir = out_path.parent / "traces"

    registry = Registry.load()
    try:
        llm = LLM(use_cache=not args.no_cache)
        tllm = triage_llm(use_cache=not args.no_cache)
    except RuntimeError as exc:  # no API key
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    orch = Orchestrator(registry, llm, args.max_tool_calls, args.max_llm_calls, triage=not args.no_triage,
                        triage_llm=tllm)
    print(f"Loaded {len(registry.tools)} tools; model {llm.model}"
          f"{'; triage model ' + tllm.model if tllm else ''}; {len(queries)} questions.", flush=True)

    # keep earlier answers when re-running a subset with --only
    answers = {}
    if args.only and out_path.exists():
        answers = {a["query_id"]: a for a in json.loads(out_path.read_text(encoding="utf-8"))}

    for i, q in enumerate(queries):
        if i and args.delay:
            time.sleep(args.delay)
        trace_path = trace_dir / f"{q['query_id']}.jsonl"
        t0 = time.time()
        try:
            entry = orch.answer(q["query_id"], q["question"], trace_path)
        except QuotaExhausted as exc:
            left = [x["query_id"] for x in queries[i:]]
            print(f"\nSTOPPED: {exc}\nNot answered yet: {' '.join(left)}\n"
                  f"Re-run later with --only {' '.join(left)} (answered questions are cached).", flush=True)
            break
        entry["trace_file"] = f"traces/{q['query_id']}.jsonl"  # relative to the answers file
        answers[q["query_id"]] = entry
        print(f"[{q['query_id']}] {entry['status']:20s} {json.dumps(entry['answer'], ensure_ascii=False)[:80]}  "
              f"({time.time() - t0:.1f}s) {q['question'][:70]}", flush=True)
        out_path.write_text(json.dumps(list(answers.values()), indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Wrote {len(answers)} answers to {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
