"""Gradio dashboard for the MSME RAG evals.

Run from the project root:  uv run python -m eval.dashboard

Tabs:
  Run evaluation  - run the eval for RAG or the baseline, optionally save it
  Saved run       - look at any saved run again without re-running (good for screenshots)
  Progress        - every saved run side by side: the "ladder" chart for the post
  Compare         - two runs question by question: what got better, what got worse
"""
from collections import defaultdict

import gradio as gr
import pandas as pd
from dotenv import load_dotenv

from eval.eval import (
    evaluate_all_retrieval, evaluate_all_answers, get_answer_fn, run_config,
)
from eval.runs import make_run, save_run, load_runs, RETRIEVAL_METRICS, ANSWER_METRICS

load_dotenv(override=True)

# (green_at_or_above, amber_at_or_above) — anything lower is red
THRESHOLDS = {
    "fraction": (0.9, 0.75),   # MRR, nDCG, coverage (all 0-1)
    "score": (4.5, 4.0),       # LLM-judge scores (1-5)
}
COLORS = {"green": "#16a34a", "amber": "#d97706", "red": "#dc2626"}
PIPELINE_COLORS = {"baseline": "#94a3b8", "rag": "#2563eb"}

METRIC_NAMES = {
    "source_mrr": "Source MRR", "ndcg": "nDCG", "keyword_mrr": "Keyword MRR",
    "page_coverage": "Page coverage", "keyword_coverage": "Keyword coverage",
    "accuracy": "Accuracy", "completeness": "Completeness", "relevance": "Relevance",
}

PLACEHOLDER = "<div style='padding: 20px; text-align: center; opacity: 0.6;'>Nothing to show yet</div>"
NO_RETRIEVAL = ("<div style='padding: 20px; text-align: center; opacity: 0.6;'>"
                "No retrieval scores: the baseline puts every page in the prompt, so there is no search step to score.</div>")


# ---------- small helpers ----------

def get_color(value: float, kind: str) -> str:
    green, amber = THRESHOLDS[kind]
    if value >= green:
        return COLORS["green"]
    if value >= amber:
        return COLORS["amber"]
    return COLORS["red"]


def metric_card(label: str, value: float, kind: str) -> str:
    color = get_color(value, kind)
    text = f"{value:.2f}/5" if kind == "score" else f"{value:.2f}"
    return f"""
    <div style="margin: 8px 0; padding: 12px 16px; border-radius: 8px;
                border: 1px solid var(--border-color-primary); border-left: 5px solid {color};">
        <div style="font-size: 13px; opacity: 0.7;">{label}</div>
        <div style="font-size: 26px; font-weight: bold; color: {color};">{text}</div>
    </div>"""


def footer(message: str) -> str:
    return f"<div style='margin-top: 12px; font-size: 13px; opacity: 0.7;'>{message}</div>"


def average(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def settings_text(run: dict) -> str:
    c = run.get("config", {})
    if run["pipeline"] == "baseline":
        return f"no retrieval · {c.get('answer_model', '?')}"
    return (f"{c.get('chunk_size')}/{c.get('chunk_overlap')} · {c.get('embedding_model')} · "
            f"k={c.get('retrieval_k')} · {c.get('answer_model')}")


def run_header(run: dict) -> str:
    return (f"**{run.get('label', run['name'])}** · {run['pipeline']} · {run['created'].replace('T', ' ')}  \n"
            f"Settings: {settings_text(run)} · judge: {run.get('config', {}).get('judge_model', '?')}")


# ---------- rendering one run (fresh or saved, same code) ----------

def retrieval_view(run: dict | None):
    empty_chart = pd.DataFrame({"Category": [], "Source MRR": []})
    if not run:
        return PLACEHOLDER, empty_chart, pd.DataFrame()
    if not run.get("retrieval"):
        return NO_RETRIEVAL, empty_chart, pd.DataFrame()

    overall = run["retrieval"]["overall"]
    questions = run["retrieval"]["questions"]
    cards = "".join([
        metric_card("Source MRR (first correct page)", overall["source_mrr"], "fraction"),
        metric_card("nDCG (all correct pages)", overall["ndcg"], "fraction"),
        metric_card("Keyword MRR", overall["keyword_mrr"], "fraction"),
        metric_card("Page coverage", overall["page_coverage"], "fraction"),
        metric_card("Keyword coverage", overall["keyword_coverage"], "fraction"),
    ]) + footer(f"Evaluated {len(questions)} questions (questions with nothing to retrieve are skipped).")

    by_category = defaultdict(list)
    for q in questions:
        by_category[q["category"]].append(q["source_mrr"])
    chart = pd.DataFrame([{"Category": c, "Source MRR": average(v)} for c, v in by_category.items()])

    table = pd.DataFrame([
        {"ID": q["id"], "Category": q["category"], "Source MRR": q["source_mrr"], "nDCG": q["ndcg"],
         "Keyword MRR": q["keyword_mrr"], "Pages": q["pages"], "Keywords": q["keywords"],
         "Question": q["question"]}
        for q in questions
    ]).sort_values(["Source MRR", "nDCG"])
    return cards, chart, table


def answer_view(run: dict | None):
    empty_chart = pd.DataFrame({"Category": [], "Accuracy": []})
    if not run or not run.get("answers"):
        return PLACEHOLDER, empty_chart, pd.DataFrame()

    overall = run["answers"]["overall"]
    questions = run["answers"]["questions"]
    cards = "".join([
        metric_card("Accuracy", overall["accuracy"], "score"),
        metric_card("Completeness", overall["completeness"], "score"),
        metric_card("Relevance", overall["relevance"], "score"),
    ]) + footer(f"Judged {len(questions)} answers.")

    by_category = defaultdict(list)
    for q in questions:
        by_category[q["category"]].append(q["accuracy"])
    chart = pd.DataFrame([{"Category": c, "Accuracy": average(v)} for c, v in by_category.items()])

    table = pd.DataFrame([
        {"ID": q["id"], "Category": q["category"], "Type": q["type"], "Accuracy": q["accuracy"],
         "Completeness": q["completeness"], "Relevance": q["relevance"],
         "Judge feedback": q["feedback"], "Answer": q["answer"]}
        for q in questions
    ]).sort_values(["Accuracy", "Completeness"])
    return cards, chart, table


# ---------- tab 1: run evaluation ----------

def run_evaluation(pipeline_label: str, save_name: str, with_answers: bool, progress=gr.Progress()):
    pipeline = "baseline" if pipeline_label == "Baseline" else "rag"
    if pipeline == "baseline" and not with_answers:
        message = "The baseline has no retrieval step. Use **Full evaluation** to score its answers."
        return (message, *retrieval_view(None), *answer_view(None))

    retrieval = None
    if pipeline == "rag":
        retrieval = []
        for test, result, prog in evaluate_all_retrieval():
            progress(prog, desc=f"Retrieval: {test.id}")
            if result is not None:
                retrieval.append((test, result))

    answers = None
    if with_answers:
        answers = []
        for test, result, answer, prog in evaluate_all_answers(get_answer_fn(pipeline)):
            progress(prog, desc=f"Answers: {test.id} (LLM calls, slower)")
            answers.append((test, result, answer))

    name = save_name.strip()
    run = make_run(name or "unsaved", pipeline, run_config(pipeline), retrieval, answers)
    if name:
        path = save_run(run)
        message = f"Saved as `results/runs/{path.name}`. It now shows in the Progress and Compare tabs."
    else:
        message = "Not saved (no name given). Type a name above to keep a run for the Progress chart."
    return (message, *retrieval_view(run), *answer_view(run))


# ---------- tab 2: saved run ----------

def find_run(label: str | None) -> dict | None:
    return next((r for r in load_runs() if r["label"] == label), None) if label else None


def show_saved_run(label: str | None):
    run = find_run(label)
    header = run_header(run) if run else "Pick a saved run."
    return (header, *retrieval_view(run), *answer_view(run))


# ---------- tab 3: progress ----------

def progress_view():
    runs = load_runs()
    if not runs:
        empty = pd.DataFrame({"Run": [], "Value": [], "Pipeline": []})
        return "No saved runs yet. Run an evaluation with a name to save it.", pd.DataFrame(), empty, empty, empty

    rows = []
    for run in runs:
        row = {"Run": run["label"], "Pipeline": run["pipeline"], "Date": run["created"][:16].replace("T", " ")}
        for m in ANSWER_METRICS:
            row[METRIC_NAMES[m]] = run["answers"]["overall"][m] if run.get("answers") else None
        for m in ["source_mrr", "ndcg", "page_coverage"]:
            row[METRIC_NAMES[m]] = run["retrieval"]["overall"][m] if run.get("retrieval") else None
        row["Settings"] = settings_text(run)
        rows.append(row)
    table = pd.DataFrame(rows)

    def chart(metric_col: str) -> pd.DataFrame:
        df = table[["Run", metric_col, "Pipeline"]].dropna().rename(columns={metric_col: "Value"})
        return df

    note = f"{len(runs)} saved runs, oldest first. Each bar is one version of the system."
    return note, table, chart("Accuracy"), chart("Source MRR"), chart("nDCG")


# ---------- tab 4: compare ----------

def compare_runs(label_a: str | None, label_b: str | None):
    run_a, run_b = find_run(label_a), find_run(label_b)
    if not run_a or not run_b:
        return "Pick two saved runs.", pd.DataFrame()

    lines = [f"**A:** {run_a['label']} ({settings_text(run_a)})  \n**B:** {run_b['label']} ({settings_text(run_b)})", ""]
    lines.append("| Metric | A | B | Change |")
    lines.append("|---|---|---|---|")
    for section, metrics in [("answers", ANSWER_METRICS), ("retrieval", RETRIEVAL_METRICS)]:
        if run_a.get(section) and run_b.get(section):
            for m in metrics:
                a, b = run_a[section]["overall"][m], run_b[section]["overall"][m]
                lines.append(f"| {METRIC_NAMES[m]} | {a:.2f} | {b:.2f} | {b - a:+.2f} |")

    def by_id(run, section):
        return {q["id"]: q for q in run[section]["questions"]} if run.get(section) else {}

    ans_a, ans_b = by_id(run_a, "answers"), by_id(run_b, "answers")
    ret_a, ret_b = by_id(run_a, "retrieval"), by_id(run_b, "retrieval")
    ids = sorted(set(ans_a) | set(ans_b) | set(ret_a) | set(ret_b))

    rows = []
    for qid in ids:
        any_q = ans_a.get(qid) or ans_b.get(qid) or ret_a.get(qid) or ret_b.get(qid)
        acc_a = ans_a.get(qid, {}).get("accuracy")
        acc_b = ans_b.get(qid, {}).get("accuracy")
        mrr_a = ret_a.get(qid, {}).get("source_mrr")
        mrr_b = ret_b.get(qid, {}).get("source_mrr")
        acc_change = acc_b - acc_a if acc_a is not None and acc_b is not None else None
        mrr_change = round(mrr_b - mrr_a, 2) if mrr_a is not None and mrr_b is not None else None
        main_change = acc_change if acc_change is not None else mrr_change
        verdict = "" if main_change is None else ("better" if main_change > 0 else "worse" if main_change < 0 else "same")
        rows.append({"ID": qid, "Category": any_q["category"], "Result": verdict,
                     "Accuracy A": acc_a, "Accuracy B": acc_b, "Accuracy change": acc_change,
                     "MRR A": mrr_a, "MRR B": mrr_b, "MRR change": mrr_change,
                     "Question": any_q["question"]})
    table = pd.DataFrame(rows)

    if not table.empty:
        counts = table["Result"].value_counts()
        lines.append("")
        lines.append(f"Per question: **{counts.get('better', 0)} better**, **{counts.get('worse', 0)} worse**, "
                     f"{counts.get('same', 0)} same (by accuracy when both runs have answers, otherwise by Source MRR).")
        order = {"worse": 0, "better": 1, "same": 2, "": 3}
        table = table.sort_values(by="Result", key=lambda s: s.map(order))
    return "\n".join(lines), table


def refresh_choices():
    labels = [r["label"] for r in load_runs()]
    latest = labels[-1] if labels else None
    previous = labels[-2] if len(labels) > 1 else latest
    return (gr.Dropdown(choices=labels, value=latest),
            gr.Dropdown(choices=labels, value=previous),
            gr.Dropdown(choices=labels, value=latest))


# ---------- layout ----------

def results_block():
    """Retrieval + answers display, used by both the Run and Saved run tabs."""
    gr.Markdown("### Retrieval  \n*RAG only. Free: no LLM calls.*")
    with gr.Row():
        with gr.Column(scale=1):
            r_cards = gr.HTML(PLACEHOLDER)
        with gr.Column(scale=2):
            r_chart = gr.BarPlot(x="Category", y="Source MRR", title="Source MRR by category",
                                 y_lim=[0, 1], height=380, sort="y")
    r_table = gr.Dataframe(label="Per question (worst first)", wrap=True)

    gr.Markdown("### Answers  \n*LLM-as-judge, scored 1-5.*")
    with gr.Row():
        with gr.Column(scale=1):
            a_cards = gr.HTML(PLACEHOLDER)
        with gr.Column(scale=2):
            a_chart = gr.BarPlot(x="Category", y="Accuracy", title="Accuracy by category",
                                 y_lim=[1, 5], height=380, sort="y")
    a_table = gr.Dataframe(label="Per question (worst first)", wrap=True)
    return [r_cards, r_chart, r_table, a_cards, a_chart, a_table]


def progress_chart(title: str, y_lim: list[float]):
    return gr.BarPlot(x="Run", y="Value", color="Pipeline", color_map=PIPELINE_COLORS,
                      title=title, y_lim=y_lim, height=320, x_label_angle=-30, sort="x")


def run_retrieval_only(pipeline_label, save_name, progress=gr.Progress()):
    return run_evaluation(pipeline_label, save_name, False, progress)


def run_full(pipeline_label, save_name, progress=gr.Progress()):
    return run_evaluation(pipeline_label, save_name, True, progress)


def main():
    with gr.Blocks(title="MSME RAG Evaluation") as app:
        gr.Markdown("# MSME RAG Evaluation Dashboard")
        gr.Markdown("Retrieval and answer quality for the Sri Lankan MSME loan assistant. "
                    "Same 33 questions and the same judge for every run.")

        with gr.Tab("Run evaluation"):
            with gr.Row():
                pipeline = gr.Radio(["RAG", "Baseline"], value="RAG", label="System to evaluate")
                save_name = gr.Textbox(label="Save as (optional)",
                                       placeholder="e.g. rag-v1, baseline, exp-date-in-prompt")
            with gr.Row():
                retrieval_button = gr.Button("Retrieval only (free)")
                full_button = gr.Button("Full evaluation (retrieval + answers, ~66 LLM calls)", variant="primary")
            run_status = gr.Markdown()
            run_outputs = results_block()

        with gr.Tab("Saved run"):
            saved_pick = gr.Dropdown(label="Saved run", choices=[])
            saved_header = gr.Markdown()
            saved_outputs = results_block()

        with gr.Tab("Progress"):
            progress_refresh = gr.Button("Refresh")
            progress_note = gr.Markdown()
            progress_accuracy = progress_chart("Answer accuracy (1-5)", [1, 5])
            with gr.Row():
                progress_mrr = progress_chart("Source MRR (RAG only)", [0, 1])
                progress_ndcg = progress_chart("nDCG (RAG only)", [0, 1])
            progress_table = gr.Dataframe(label="All saved runs", wrap=True)

        with gr.Tab("Compare"):
            with gr.Row():
                compare_a = gr.Dropdown(label="Run A (before)", choices=[])
                compare_b = gr.Dropdown(label="Run B (after)", choices=[])
            compare_button = gr.Button("Compare", variant="primary")
            compare_summary = gr.Markdown()
            compare_table = gr.Dataframe(label="Per question (worse first)", wrap=True)

        dropdowns = [saved_pick, compare_a, compare_b]
        progress_outputs = [progress_note, progress_table, progress_accuracy, progress_mrr, progress_ndcg]

        retrieval_button.click(
            run_retrieval_only,
            inputs=[pipeline, save_name], outputs=[run_status, *run_outputs],
        ).then(refresh_choices, outputs=dropdowns).then(progress_view, outputs=progress_outputs)
        full_button.click(
            run_full,
            inputs=[pipeline, save_name], outputs=[run_status, *run_outputs],
        ).then(refresh_choices, outputs=dropdowns).then(progress_view, outputs=progress_outputs)

        saved_pick.change(show_saved_run, inputs=saved_pick, outputs=[saved_header, *saved_outputs])
        progress_refresh.click(progress_view, outputs=progress_outputs).then(refresh_choices, outputs=dropdowns)
        compare_button.click(compare_runs, inputs=[compare_a, compare_b], outputs=[compare_summary, compare_table])

        app.load(progress_view, outputs=progress_outputs).then(refresh_choices, outputs=dropdowns)

    app.launch(inbrowser=True, theme=gr.themes.Soft())


if __name__ == "__main__":
    main()
