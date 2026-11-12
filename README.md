# Graph Analytics Orchestrator

An LLM agent that answers natural-language questions about the course graphs (airports, karate,
lesmis, courses, projects). It plans tool calls, runs tools from the class registry, chains them
through `result_graph_id`, and writes a structured answer plus a full trace for every question.
It is plain Python (our own agent loop) on an OpenAI-compatible API; the default provider is Google Gemini's free tier.

## Setup

You need Python 3.10 or later.

```
python -m venv .venv
.venv\Scripts\activate             # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
```

**API key.** The key is read from the environment variable **`LLM_API_KEY`**. Either set it in
your shell, or copy `.env.example` to `.env` and fill it in (`.env` is git-ignored; never commit it).
Optional variables:

| Variable | Default | Meaning |
| --- | --- | --- |
| `LLM_API_KEY` | (required) | API key for the provider |
| `LLM_BASE_URL` | Gemini's OpenAI-compatible endpoint | Change it to use Groq, OpenRouter or Ollama (see `.env.example`) |
| `LLM_MODEL` | `gemini-3.5-flash-lite` | Any model with function calling; used for planning and as a triage judge |
| `LLM_BACKUP_MODEL` | `gemini-2.5-flash` (on Gemini) | Second model; the run switches to it when `LLM_MODEL`'s quota runs out |
| `LLM_TRIAGE_MODEL` | (none: one judge, `LLM_MODEL`) | Optional second triage judge; we use Groq `openai/gpt-oss-120b` |
| `LLM_TRIAGE_BASE_URL`, `LLM_TRIAGE_API_KEY` | `LLM_BASE_URL`, `LLM_API_KEY` | Provider and key for that model, e.g. Groq (see `.env.example`) |
| `LLM_CACHE` | `1` | `0` disables the LLM response cache in `cache/llm/` |

## Run

```
python run_queries.py --queries <file> --out answers.json
```

This writes `answers.json` and one trace per question in `traces/` next to it. Run commands from
this folder. Useful options: `--only q03 q07` (re-run some questions and keep the other answers),
`--delay 5` (wait between questions on tight rate limits), `--no-cache`, `--no-triage` (skip the
triage step, for comparison).

**Free-tier quotas.** Gemini's free tier has small per-model daily request limits (about 20 a day
for some flash models), and a question takes 2 to 4 LLM calls. If the quota runs out, the runner
stops at once, says which questions are left, and you can continue later with `--only`. Answered
questions come from the cache and cost nothing. You can also switch models, since quotas are per
model (e.g. `LLM_MODEL=gemini-3.5-flash-lite`, which we also tested), or switch provider.

The queries file can be a JSON list (or `{"queries": [...]}`) of objects with `query_id` and
`question`, JSON Lines, or a plain text file with one question per line.

The public set is in `queries/public_queries.json`, converted from the instructors' spreadsheet
with `python queries/convert_public.py <xlsx>` (that one script needs `pip install openpyxl`).
To run it and score the answers:

```
python run_queries.py --queries queries/public_queries.json --out answers_public.json
python evaluate.py --answers answers_public.json --expected queries/public_queries.json
```

Numbers are scored within 0.1%, node lists as sets or in order for rankings, the course order by
checking every prerequisite comes first, and ambiguous/unsupported questions by status only.

## What is in here

| Path | What it is |
| --- | --- |
| `run_queries.py` | The one-command runner |
| `orchestrator/registry.py` | Discovers tools by reading every `tool.json` under `infra_tools/` and `registry/tools/` at startup |
| `orchestrator/agent.py` | The agent loop: plan, call tools, chain results, finish with `final_answer` |
| `orchestrator/prompts.py` | System prompt (built from the graph store) and the `final_answer` function schema |
| `orchestrator/answers.py` | Builds the structured answer and checks that the trace supports it |
| `orchestrator/llm_client.py` | OpenAI-compatible client with an on-disk response cache and rate-limit retries |
| `registry/tools/` | The 33 implementations we chose, one per tool (see `curation/report.md`) |
| `infra_tools/` | The four instructor tools: `list_graphs`, `lookup_node`, `node_attributes`, `filter_nodes` |
| `curation/` | `curate.py` tests every class implementation against NetworkX and installs the winners |
| `queries/` | Our practice questions with expected answers, and the script that builds them |
| `evaluate.py` | Scores an answers file against expected answers |
| `graphkit/`, `data/` | Shared library and datasets from the Assignment 3 starter kit (unchanged) |

## How it works

1. **Tool discovery.** At startup `Registry.load()` reads every manifest in `infra_tools/` and
   `registry/tools/` and turns it into a function schema. No tool name is hard-coded in the loop.
2. **Triage.** A small LLM step first decides only whether the question can be answered as written:
   proceed, clarification_needed or unsupported. It sees the graph catalogue and one line per tool,
   not the full schemas, so the model can focus on that one decision. A clarification_needed decision
   must list at least two readings, otherwise it is ignored. When a second model is configured
   (`LLM_TRIAGE_*`), both judge the question and it stops only when they reach the same decision:
   different models raise different false alarms, and agreement filters them out. Otherwise, or if a
   reply cannot be read, planning runs as usual, so triage never stops an answerable question from
   being tried.
3. **Planning and execution.** The LLM sees the graph catalogue (built from the store: description,
   direction, weights, node attributes, example ids) and all tool schemas plus a `final_answer`
   function. Each turn it calls tools; we run them on a fresh `GraphStore` per question and send the
   outputs back. Subgraph ids returned by community, component, filter, ego and k-hop tools are passed
   as `graph_id` to later tools, which is how multi-step questions are chained.
4. **Finishing.** The LLM must call `final_answer` with a status (`answered`,
   `clarification_needed`, `unsupported`, `error`), an answer type and a typed value. We check the
   answer against the trace before accepting it: node ids must be real ids that appeared in a tool
   output, numbers must appear in a tool output (or the model must confirm it computed them), and an
   `answered` status needs at least one successful tool call. Rejected answers go back to the model
   with the reason.
5. **Conventions.** Centrality scores are unweighted by default, matching the reference answers
   (NetworkX defaults). For any tool whose manifest category is `centrality` and that has a
   `weighted` or `use_weights` option, the executor sets it to false unless the planner passes it.
   The trace logs the arguments actually used.
6. **Budgets.** At most 6 graph tool calls and 10 LLM calls per question. Once the tool budget is
   used, only `final_answer` is offered.
7. **Traces.** `traces/<query_id>.jsonl` logs the question, the configuration, every LLM call (input
   messages since the previous call, the response, token usage, whether it came from the cache),
   every tool call with arguments and output, rejected answers, the final answer and its structured form.

## Results on the public set

| Configuration | Score | Wrong |
| --- | --- | --- |
| `gemini-3.5-flash-lite`, no triage (`--no-triage`) | 29/30 | q26 (answered an ambiguous question) |
| `gemini-3.5-flash-lite` + triage with Groq `openai/gpt-oss-120b` as second judge | **30/30** | none |

`answers_public.json` and `traces/` come from the 30/30 configuration. With only `LLM_API_KEY` set,
triage has one judge (`LLM_MODEL`); in our tests that judge alone also misjudged one question.

## Tool curation

All 186 class implementations pass the contract validator, so validation alone cannot choose.
`curation/curate.py` runs every implementation on test cases from the five datasets and compares the
output with NetworkX (centrality scores, path lengths, flow values, component and community
partitions, triangle counts, and so on). It scores each implementation, then breaks ties by
determinism, speed, useful options (`node`, `direction`, `weighted`, ...) and description quality.
The report is in `curation/report.md`. To repeat it (needs `pip install -r curation/requirements.txt`
and the full class registry checked out next to this folder as `../tools`):

```
python curation/curate.py --raw ../tools --install
```

NetworkX and SciPy are used only in curation and in `queries/make_sample_queries.py`, never by the
orchestrator or the tools. We did not edit any registry tool.
