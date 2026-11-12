"""Tool discovery: read every manifest under the tool folders at startup. Nothing is hard-coded.

    reg = Registry.load()                    # infra_tools/ + registry/tools/
    reg.schemas()                            # OpenAI-style function schemas for the LLM
    reg.call(store, "pagerank", {...})       # run a tool, never raises
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from graphkit.contract import error
from graphkit.llm import tool_schema
from graphkit.loader import Tool, discover

ROOT = Path(__file__).resolve().parent.parent
TOOL_ROOTS = (ROOT / "infra_tools", ROOT / "registry" / "tools")
MAX_OUTPUT_CHARS = 12_000  # tools already keep outputs under 8 KB; this is a safety net
WEIGHT_OPTIONS = ("weighted", "use_weights")


@dataclass
class Registry:
    tools: dict[str, Tool] = field(default_factory=dict)

    @classmethod
    def load(cls, roots=TOOL_ROOTS) -> "Registry":
        reg = cls()
        for tool in discover(*[r for r in roots if Path(r).is_dir()]):
            if tool.name in reg.tools:
                raise RuntimeError(f"Two implementations of '{tool.name}' are installed "
                                   f"({reg.tools[tool.name].path} and {tool.path}); keep only one.")
            reg.tools[tool.name] = tool
        if not reg.tools:
            raise RuntimeError(f"No tools found under {', '.join(map(str, roots))}.")
        return reg

    def schemas(self) -> list[dict]:
        return [tool_schema(t.manifest) for t in self.tools.values()]

    def implementation_id(self, name: str) -> str:
        return self.tools[name].implementation_id if name in self.tools else name

    def prepare(self, name: str, arguments: dict) -> dict:
        """The arguments a call will actually use: type slips fixed, conventions applied.

        Convention (as in the course's reference answers): centrality scores are unweighted unless
        the caller asks for weights, so a centrality tool's weighted/use_weights option defaults to false.
        """
        tool = self.tools.get(name)
        if tool is None:
            return dict(arguments)
        props = tool.manifest.get("parameters", {}).get("properties", {})
        args = _coerce(arguments, props)
        if tool.manifest.get("category") == "centrality":
            for opt in WEIGHT_OPTIONS:
                if props.get(opt, {}).get("type") == "boolean" and opt not in args:
                    args[opt] = False
        return args

    def call(self, store, name: str, arguments: dict) -> dict:
        """Run a tool by name with prepared arguments. Unknown tools, bad arguments and crashes come back as error dicts."""
        tool = self.tools.get(name)
        if tool is None:
            return error(f"Unknown tool '{name}'. Available tools: {', '.join(sorted(self.tools))}.")
        out = tool.call(store, **arguments)
        if not isinstance(out, dict):
            return error(f"Tool '{name}' returned {type(out).__name__} instead of a result dict.")
        text = json.dumps(out, ensure_ascii=False, default=str)
        if len(text) > MAX_OUTPUT_CHARS:
            out = dict(out, result="(truncated: output too large; ask for fewer results with top_k)")
        return out


def _coerce(arguments: dict, props: dict) -> dict:
    """Fix the small type slips LLMs make (5.0 or "5" for an integer, "true" for a boolean)."""
    fixed = {}
    for key, value in arguments.items():
        typ = props.get(key, {}).get("type")
        if typ == "integer" and isinstance(value, float) and value.is_integer():
            value = int(value)
        elif typ == "integer" and isinstance(value, str) and value.strip().lstrip("-").isdigit():
            value = int(value)
        elif typ == "number" and isinstance(value, str):
            try:
                value = float(value)
            except ValueError:
                pass
        elif typ == "boolean" and isinstance(value, str) and value.lower() in ("true", "false"):
            value = value.lower() == "true"
        fixed[key] = value
    return fixed
