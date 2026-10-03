"""Re-grade every saved run with the current golden set and grader, without re-running models.

Used when the grader is corrected (e.g. accepting "四個" as well as "4個"); every run is
re-graded with the same rules so model comparisons stay fair.
"""

import json
import sys
from pathlib import Path

from aorus_rag.benchmark import grade, load_cases, summarize, to_markdown

RES = Path(__file__).resolve().parent / "results"


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    for path in sorted(RES.glob("*.json")):
        res = json.loads(path.read_text(encoding="utf-8"))
        if "rows" not in res:
            continue
        # each run records its question set (held-out runs use heldout_qa.jsonl)
        qfile = RES.parent / res.get("questions", "golden_qa.jsonl")
        cases = {c["id"]: c for c in load_cases(qfile)}
        if "cache_tokens" not in res["rows"][0]:
            # The very first run predates the benchmark fixes; it is kept untouched as a record.
            print(f"{path.stem:42s} (legacy format, left untouched)")
            continue
        before = res["summary"]["overall"]["acc"]
        for row in res["rows"]:
            case = cases[row["id"]]
            row.update(grade(case, row["answer"], row["context"]))
            if "answers_all" in row:
                row["correct_runs"] = [grade(case, a, row["context"])["correct"] for a in row["answers_all"]]
        res["summary"] = summarize(res["rows"])
        path.write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
        path.with_suffix(".md").write_text(to_markdown(res), encoding="utf-8")  # keep .md in sync
        after = res["summary"]["overall"]["acc"]
        flag = "" if before == after else "   <- changed"
        print(f"{path.stem:42s} {before:6.1%} -> {after:6.1%}{flag}")


if __name__ == "__main__":
    main()
