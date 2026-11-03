"""Save and load eval runs as JSON files in results/runs/.

One file = one run of one version of the system (baseline, RAG v1, an experiment...).
The dashboard reads these files to draw progress charts and compare runs, so old
versions stay visible even after the code has changed.
"""
import json
import re
from datetime import datetime
from pathlib import Path

RUNS_DIR = Path(__file__).parent.parent / "results" / "runs"

RETRIEVAL_METRICS = ["source_mrr", "ndcg", "keyword_mrr", "page_coverage", "keyword_coverage"]
ANSWER_METRICS = ["accuracy", "completeness", "relevance"]


def _average(values: list[float]) -> float:
    return round(sum(values) / len(values), 3) if values else 0.0


def make_run(name: str, pipeline: str, config: dict, retrieval=None, answers=None) -> dict:
    """Build a run record.
    retrieval: list of (TestQuestion, RetrivalEval)        - None for the baseline
    answers:   list of (TestQuestion, AnswerEval, answer, tokens) - None for a retrieval-only run
               (tokens = rag.usage.snapshot() for that question)
    """
    run = {
        "name": name,
        "pipeline": pipeline,
        "created": datetime.now().isoformat(timespec="seconds"),
        "config": config,
        "retrieval": None,
        "answers": None,
    }
    if retrieval:
        questions = [
            {"id": t.id, "category": t.category, "question": t.question,
             **{m: round(getattr(r, m), 3) for m in RETRIEVAL_METRICS},
             "pages": f"{r.pages_found}/{r.total_pages}",
             "keywords": f"{r.keywords_found}/{r.total_keywords}"}
            for t, r in retrieval
        ]
        run["retrieval"] = {
            "overall": {m: _average([q[m] for q in questions]) for m in RETRIEVAL_METRICS},
            "questions": questions,
        }
    if answers:
        questions = [
            {"id": t.id, "category": t.category, "type": t.type, "question": t.question,
             **{m: getattr(r, m) for m in ANSWER_METRICS},
             "feedback": r.feedback, "answer": answer, **tokens}
            for t, r, answer, tokens in answers
        ]
        run["answers"] = {
            "overall": {m: _average([q[m] for q in questions]) for m in ANSWER_METRICS},
            "tokens": {
                "avg_prompt": _average([q["prompt_tokens"] for q in questions]),
                "avg_completion": _average([q["completion_tokens"] for q in questions]),
                "avg_total": _average([q["total_tokens"] for q in questions]),
                "total": sum(q["total_tokens"] for q in questions),
            },
            "questions": questions,
        }
    return run


def save_run(run: dict) -> Path:
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", run["name"]).strip("-").lower() or "run"
    stamp = datetime.fromisoformat(run["created"]).strftime("%Y-%m-%d_%H%M%S")
    path = RUNS_DIR / f"{stamp}_{slug}.json"
    path.write_text(json.dumps(run, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def load_runs() -> list[dict]:
    """All saved runs, oldest first. Each gets a unique 'label' like '02. rag-v1' for charts
    (zero-padded so the charts keep them in order)."""
    runs = []
    for path in sorted(RUNS_DIR.glob("*.json")):
        run = json.loads(path.read_text(encoding="utf-8"))
        run["file"] = path.name
        runs.append(run)
    runs.sort(key=lambda r: r["created"])
    for index, run in enumerate(runs, start=1):
        run["label"] = f"{index:02d}. {run['name']}"
    return runs
