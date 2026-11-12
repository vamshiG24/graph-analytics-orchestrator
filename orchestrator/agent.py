"""The agent loop: the LLM plans tool calls, we execute them, and it finishes with final_answer.

One question = one fresh GraphStore (so subgraph ids start at ~1 every time and runs are
reproducible), one trace file, and a bounded number of LLM and tool calls.
"""
from __future__ import annotations

import ast
import json
from pathlib import Path

from graphkit import GraphStore
from graphkit.trace import Trace

from .answers import build_answer, grounding_problems
from .llm_client import LLM, QuotaExhausted
from .prompts import FINAL_ANSWER_TOOL, TRIAGE_TOOL, system_prompt, tool_result_message, triage_prompt
from .registry import Registry

MAX_TOOL_CALLS = 6   # graph tool calls per question
MAX_LLM_CALLS = 10   # LLM calls per question (including retries after a rejected answer)
TRIAGE_DECISIONS = ("proceed", "clarification_needed", "unsupported")


def _parse_args(raw) -> tuple[dict | None, str | None]:
    if isinstance(raw, dict):
        return raw, None
    try:
        args = json.loads(raw or "{}")
    except json.JSONDecodeError as exc:
        return None, f"Arguments are not valid JSON ({exc}). Send a JSON object."
    if not isinstance(args, dict):
        return None, "Arguments must be a JSON object."
    return args, None


def _reply(call: dict, payload: dict) -> dict:
    """The message answering a final_answer call (a user message if the model wrote the call as text)."""
    if call.get("id") is None:
        return {"role": "user", "content": "final_answer result: " + json.dumps(payload, ensure_ascii=False)}
    return tool_result_message(call["id"], payload)


def _call_from_text(content, name: str = "final_answer") -> dict | None:
    """Arguments of a name(...) call that the model wrote as plain text, or None.

    Parsed with ast and literal_eval only: the text is never executed.
    """
    if not isinstance(content, str) or f"{name}(" not in content:
        return None
    text = content.strip().strip("`").strip()
    if text.startswith("python"):
        text = text[len("python"):].strip()
    try:
        node = ast.parse(text, mode="eval").body
    except SyntaxError:
        return None
    if not (isinstance(node, ast.Call) and getattr(node.func, "id", None) == name) or node.args:
        return None
    try:
        return {kw.arg: ast.literal_eval(kw.value) for kw in node.keywords if kw.arg}
    except ValueError:
        return None


class Orchestrator:
    def __init__(self, registry: Registry, llm: LLM, max_tool_calls: int = MAX_TOOL_CALLS,
                 max_llm_calls: int = MAX_LLM_CALLS, triage: bool = True,
                 triage_llm: LLM | None = None):
        self.registry = registry
        self.triage = triage
        # triage judges: the main LLM, plus a second model when one is configured (LLM_TRIAGE_*)
        self.judges = [triage_llm, llm] if triage_llm is not None and triage_llm is not llm else [llm]
        self.llm = llm
        self.max_tool_calls = max_tool_calls
        self.max_llm_calls = max_llm_calls
        self.graph_schemas = registry.schemas()

    def _triage(self, question: str, store: GraphStore, trace: Trace) -> tuple[dict | None, int]:
        """A small LLM step that only decides proceed / clarification_needed / unsupported.

        It sees the graphs and one line per tool, not the full schemas, so the model can focus
        on whether the question is clear and computable. With two judges (a second model set
        through LLM_TRIAGE_*), the question stops here only when both independently reach the
        same non-proceed decision: different models make different false alarms, and agreement
        filters them out. Returns (decision or None, LLM calls used); None means proceed, also
        when a reply cannot be read, so a triage hiccup never blocks an answerable question.
        """
        manifests = [t.manifest for t in self.registry.tools.values()]
        messages = [{"role": "system", "content": triage_prompt(store, manifests)},
                    {"role": "user", "content": question}]
        decisions, calls = [], 0
        for judge in self.judges:
            args = self._judge(judge, messages, trace)
            calls += 1
            if args is None or (decisions and args["decision"] != decisions[0]["decision"]):
                trace.event("triage", decision="proceed", judges=[d["decision"] for d in decisions] +
                            [args["decision"] if args else "proceed"],
                            note="no agreement on stopping; proceeding to planning")
                return None, calls
            decisions.append(args)
        trace.event("triage", **decisions[0], judges=[d["decision"] for d in decisions])
        return decisions[0], calls

    def _judge(self, judge: LLM, messages: list[dict], trace: Trace) -> dict | None:
        """One judge's decision when it says stop (clarification_needed / unsupported), else None."""
        args, _ = self._triage_call(judge, messages, trace)
        if not isinstance(args, dict) or args.get("decision") not in TRIAGE_DECISIONS:
            trace.event("triage_judge", model=judge.model, decision=None, note="unreadable reply")
            return None
        readings = args.get("readings")
        if args["decision"] == "clarification_needed" and isinstance(readings, list) and len(readings) < 2:
            # an ambiguity needs at least two readings; one listed reading contradicts the decision
            trace.event("triage_judge", model=judge.model, **args, overridden="only one reading listed")
            return None
        trace.event("triage_judge", model=judge.model, **args)
        return None if args["decision"] == "proceed" else args

    def _triage_call(self, judge: LLM, messages: list[dict], trace: Trace) -> tuple[dict | None, dict]:
        message, info = judge.chat(messages, [TRIAGE_TOOL])
        trace.event("llm_call", stage="triage", model=judge.model, input_messages=messages, response=message, **info)
        for call in message.get("tool_calls") or []:
            if call.get("function", {}).get("name") == "triage":
                return _parse_args(call["function"].get("arguments"))[0], message
        return _call_from_text(message.get("content"), "triage"), message

    def answer(self, query_id: str, question: str, trace_path: Path) -> dict:
        trace = Trace(trace_path)
        trace.question(question)
        trace.event("config", model=self.llm.model, tools=sorted(self.registry.tools),
                    max_tool_calls=self.max_tool_calls, max_llm_calls=self.max_llm_calls)
        store = GraphStore()
        messages = [{"role": "system", "content": system_prompt(store, list(self.registry.tools), self.max_tool_calls)},
                    {"role": "user", "content": question}]
        tool_outputs: list[dict] = []
        tools_used: list[str] = []
        n_tool_calls = n_llm_calls = 0
        rejected_once: set[str] = set()   # grounding warnings already given (a repeat call is accepted)
        nudges = 0
        logged = 0  # messages already written to the trace

        def finish(status, answer, text):
            entry = {"query_id": query_id, "status": status, "answer_text": text, "answer": answer,
                     "tools_used": tools_used, "trace_file": None}
            trace.final_answer(text)
            trace.event("answer", status=status, answer=answer, tools_used=tools_used,
                        llm_calls=n_llm_calls, tool_calls=n_tool_calls)
            return entry

        try:
            if self.triage:
                decision, used = self._triage(question, store, trace)
                n_llm_calls += used
                if decision and decision["decision"] != "proceed":
                    text = decision.get("answer_text") or f"The question is {decision['decision'].replace('_', ' ')}."
                    return finish(decision["decision"], {"type": "text", "value": text}, text)
            while n_llm_calls < self.max_llm_calls:
                budget_left = n_tool_calls < self.max_tool_calls
                tools = self.graph_schemas + [FINAL_ANSWER_TOOL] if budget_left else [FINAL_ANSWER_TOOL]
                message, info = self.llm.chat(messages, tools)
                n_llm_calls += 1
                trace.event("llm_call", model=self.llm.model, input_messages=messages[logged:],
                            response=message, **info)
                messages.append(message)
                logged = len(messages)
                calls = message.get("tool_calls") or []

                text_final = _call_from_text(message.get("content")) if not calls else None
                if text_final is not None:  # some models write the call out as text instead of making it
                    trace.event("final_answer_from_text", arguments=text_final)
                    calls = [{"id": None, "function": {"name": "final_answer", "arguments": text_final}}]
                if not calls:
                    nudges += 1
                    if nudges > 2:
                        return finish("error", {"type": "text", "value": message.get("content") or ""},
                                      "The model did not produce a final answer.")
                    messages.append({"role": "user", "content": "Do not reply in plain text. Call the tools you need, "
                                                                "then call final_answer."})
                    continue

                final_call = None
                for call in calls:
                    name = call.get("function", {}).get("name", "")
                    args, problem = _parse_args(call.get("function", {}).get("arguments"))
                    if name == "final_answer":
                        final_call = (call, args, problem)
                        continue
                    if problem:
                        output = {"status": "error", "result": None, "summary": problem, "result_graph_id": None, "error": problem}
                    elif n_tool_calls >= self.max_tool_calls:
                        output = {"status": "error", "result": None, "result_graph_id": None,
                                  "summary": "Tool budget used up.", "error": "Tool budget used up: call final_answer now."}
                    else:
                        args = self.registry.prepare(name, args)  # logged as actually used
                        output = self.registry.call(store, name, args)
                        n_tool_calls += 1
                    trace.tool_call(name, args if args is not None else {}, output)
                    tool_outputs.append(output)
                    if output.get("status") == "ok":
                        impl = self.registry.implementation_id(name)
                        if impl not in tools_used:
                            tools_used.append(impl)
                    messages.append(tool_result_message(call.get("id", ""), output))

                if final_call is None:
                    if n_tool_calls >= self.max_tool_calls:
                        messages.append({"role": "user", "content": "You have used all tool calls. Call final_answer now "
                                                                    "with what the tool outputs support."})
                    continue

                call, args, problem = final_call
                if len(calls) > 1:
                    reply = "final_answer was called together with other tools. Read their outputs first, then call final_answer again on its own."
                    trace.event("final_answer_rejected", arguments=args, reason=reply)
                    messages.append(_reply(call, {"status": "error", "error": reply}))
                    continue
                answer, problem = (None, problem) if problem else build_answer(args)
                if answer is not None:
                    issues = grounding_problems(answer, args["status"], tool_outputs, store)
                    fresh = [i for i in issues if i not in rejected_once or i.startswith("You answered without")]
                    if fresh:
                        rejected_once.update(fresh)
                        problem = " ".join(fresh)
                if problem:
                    trace.event("final_answer_rejected", arguments=args, reason=problem)
                    messages.append(_reply(call, {"status": "error", "error": problem}))
                    continue
                messages.append(_reply(call, {"status": "ok"}))
                return finish(args["status"], answer, args.get("answer_text", ""))

            return finish("error", {"type": "text", "value": ""},
                          f"Stopped after {n_llm_calls} LLM calls without an accepted final answer.")
        except QuotaExhausted as exc:
            trace.error(str(exc))
            raise  # the runner stops: every further question would fail the same way
        except Exception as exc:  # network down, provider error, ...
            trace.error(f"{type(exc).__name__}: {exc}")
            return finish("error", {"type": "text", "value": ""}, f"Error: {type(exc).__name__}: {str(exc)[:300]}")
