"""Survey every registry implementation: validator result, parameters, sample output."""
import json, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from graphkit.validate import validate
from graphkit.loader import load_tool
from graphkit import GraphStore

RAW = Path(sys.argv[1])
out = {}
for tdir in sorted(RAW.iterdir()):
    for idir in sorted(tdir.iterdir()):
        rep = validate(idir)
        m = json.loads((idir / "tool.json").read_text(encoding="utf-8"))
        entry = {"errors": rep.errors, "warnings": [w for w in rep.warnings if "test functions" not in w],
                 "params": {k: {kk: vv for kk, vv in v.items() if kk != "description"} for k, v in m["parameters"].get("properties", {}).items()},
                 "required": m["parameters"].get("required", []), "examples": m.get("examples", []),
                 "desc_len": len(m.get("description", ""))}
        if not rep.errors:
            tool = load_tool(idir)
            ex = dict(m["examples"][0])
            t = time.time(); o = tool.call(GraphStore(), **ex); entry["ex_time"] = round(time.time() - t, 3)
            entry["sample"] = json.dumps(o)[:600]
        out[f"{tdir.name}/{idir.name}"] = entry
        print(tdir.name, idir.name, "PASS" if not rep.errors else "FAIL " + "; ".join(rep.errors)[:200], flush=True)
(ROOT / "curation" / "survey.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
