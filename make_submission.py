"""Build the submission zip without secrets or local clutter.

    python make_submission.py --answers runs/public/answers.json --out submission.zip

Includes the code, registry, data, README and curation report, plus the answers file (as
answers_public.json) and its traces/ folder. Never includes .env, .venv, cache/ or __pycache__.
"""
import argparse
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
INCLUDE = ["README.md", "requirements.txt", ".env.example", ".gitignore", "run_queries.py", "evaluate.py",
           "make_submission.py", "run_tool.py", "smoke_test.py", "orchestrator", "registry", "infra_tools",
           "graphkit", "data", "curation", "queries"]
SKIP_PARTS = {".env", ".venv", "venv", "cache", "__pycache__", ".pytest_cache", "runs"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--answers", required=True, help="answers file of the public set")
    ap.add_argument("--report", help="optional report PDF to include")
    ap.add_argument("--out", default="submission.zip")
    args = ap.parse_args()
    answers = Path(args.answers)
    with zipfile.ZipFile(args.out, "w", zipfile.ZIP_DEFLATED) as z:
        for item in INCLUDE:
            p = ROOT / item
            files = [p] if p.is_file() else sorted(f for f in p.rglob("*") if f.is_file())
            for f in files:
                rel = f.relative_to(ROOT)
                if SKIP_PARTS & set(rel.parts) or f.suffix == ".pyc":
                    continue
                z.write(f, rel.as_posix())
        z.write(answers, "answers_public.json")
        for f in sorted((answers.parent / "traces").glob("*.jsonl")):
            z.write(f, f"traces/{f.name}")
        if args.report:
            z.write(args.report, Path(args.report).name)
    names = zipfile.ZipFile(args.out).namelist()
    assert not any(n == ".env" or n.endswith("/.env") for n in names), "refusing: .env in zip"
    print(f"Wrote {args.out} with {len(names)} files")


if __name__ == "__main__":
    main()
