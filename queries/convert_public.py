"""Convert the instructors' public query spreadsheet into queries/public_queries.json.

    python queries/convert_public.py "queries/CS6855_Public_Query_Set (1).xlsx"

Needs openpyxl (pip install openpyxl); run_queries.py itself only reads the JSON.
Keeps the expected answers so evaluate.py can score a run. "Ranked: order matters" in the
notes becomes "ordered": true; a note saying to grade by checking prerequisites becomes
"check": "topological_order".
"""
import json
import sys
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parent.parent


def parse_value(atype, raw):
    text = str(raw).strip()
    if atype == "number":
        return float(text.replace(",", "")) if "." in text else int(text.replace(",", ""))
    if atype == "boolean":
        return text.lower() == "true"
    if atype == "node":
        return text
    if atype == "node_list":
        return [t.strip() for t in text.split(",") if t.strip()]
    if atype == "path":
        return [t.strip() for t in text.replace("->", "→").split("→") if t.strip()]
    return text


def kind_of(status, qnum):
    if status == "clarification_needed":
        return "ambiguous"
    if status == "unsupported":
        return "unsupported"
    return "single" if qnum <= 14 else "multi"


def main(path):
    ws = openpyxl.load_workbook(path, data_only=True)["Queries"]
    rows = list(ws.iter_rows(values_only=True))
    header = [str(h).strip() if h else "" for h in rows[0]]
    col = {h: i for i, h in enumerate(header)}
    out = []
    for row in rows[1:]:
        qid = row[col["Query ID"]]
        if not qid or not str(qid).startswith("q"):
            continue
        status = row[col["Expected status"]].strip()
        notes = (row[col["Notes"]] or "") + " " + (row[col["Working (NetworkX)"]] or "")
        q = {"query_id": qid, "question": row[col["Question"]].strip(), "graph": row[col["Graph"]],
             "kind": kind_of(status, int(qid[1:])), "expected": {"status": status}}
        if status == "answered":
            atype = row[col["Answer type"]].strip()
            q["expected"]["answer"] = {"type": atype, "value": parse_value(atype, row[col["Expected answer"]])}
            if "order matters" in notes.lower():
                q["expected"]["ordered"] = True
            if "prerequisite comes" in notes.lower():
                q["expected"]["check"] = "topological_order"
        q["notes"] = (row[col["Notes"]] or "").strip()
        out.append(q)
    dest = ROOT / "queries" / "public_queries.json"
    dest.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {len(out)} queries to {dest}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else ROOT / "queries" / "CS6855_Public_Query_Set (1).xlsx")
