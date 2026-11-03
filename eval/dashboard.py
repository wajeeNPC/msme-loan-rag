"""Gradio dashboard for the MSME RAG evals.

Run from the project root:  uv run python -m eval.dashboard

Workflow on the first tab:  1 choose a system -> 2 run -> 3 review results -> save.

Tabs:
  Run evaluation  - run the eval for RAG or the baseline, then save it under a name
  Saved run       - look at any saved run again without re-running (good for screenshots)
  Progress        - every saved run side by side: the "ladder" chart for the post
  Compare         - two runs question by question: what got better, what got worse
"""
import html
from collections import defaultdict

import gradio as gr
import pandas as pd
from dotenv import load_dotenv

from eval.eval import (
    evaluate_all_retrieval, evaluate_all_answers, get_answer_fn, get_fetch_fn, run_config,
)
from rag_pro import config as pro_config
from eval.runs import make_run, save_run, load_runs, RETRIEVAL_METRICS, ANSWER_METRICS

load_dotenv(override=True)

# (green_at_or_above, amber_at_or_above) — anything lower is red
THRESHOLDS = {
    "fraction": (0.9, 0.75),   # MRR, nDCG, coverage (all 0-1)
    "score": (4.5, 4.0),       # LLM-judge scores (1-5)
}
COLORS = {"green": "#22c55e", "amber": "#f59e0b", "red": "#ef4444"}
LEVEL_WORDS = {COLORS["green"]: "Good", COLORS["amber"]: "Fair", COLORS["red"]: "Weak"}
BANNER_COLORS = {"idle": "#94a3b8", "running": "#3b82f6", "done": "#22c55e",
                 "warn": "#f59e0b", "error": "#ef4444"}
PIPELINE_COLORS = {"baseline": "#94a3b8", "rag": "#2563eb", "rag_pro": "#7c3aed"}
PIPELINES = {"RAG": "rag", "RAG Pro": "rag_pro", "Baseline": "baseline"}   # radio label -> run["pipeline"]

METRIC_NAMES = {
    "source_mrr": "Source MRR", "ndcg": "nDCG", "keyword_mrr": "Keyword MRR",
    "page_coverage": "Page coverage", "keyword_coverage": "Keyword coverage",
    "accuracy": "Accuracy", "completeness": "Completeness", "relevance": "Relevance",
}

RETRIEVAL_LABEL = "Retrieval only (no answers or judge)"

PLACEHOLDER = "<div style='padding: 20px; text-align: center; opacity: 0.6;'>Nothing to show yet</div>"

THEME = gr.themes.Soft(
    primary_hue="blue", neutral_hue="slate",
    font=[gr.themes.GoogleFont("Fira Sans"), "ui-sans-serif", "system-ui", "sans-serif"],
    font_mono=[gr.themes.GoogleFont("Fira Code"), "ui-monospace", "monospace"],
)


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
    # The word (Good/Fair/Weak) means colour is never the only signal.
    return f"""
    <div style="padding: 12px 14px; border-radius: 8px; border: 1px solid var(--border-color-primary);
                border-top: 3px solid {color};">
        <div style="font-size: 13px; opacity: 0.8;">{label}</div>
        <div style="font-size: 26px; font-weight: 600; color: {color};
                    font-variant-numeric: tabular-nums;">{text}</div>
        <div style="font-size: 12px; color: {color};">{LEVEL_WORDS[color]}</div>
    </div>"""


def info_card(label: str, text: str, sub: str) -> str:
    """A neutral card for numbers with no good/bad threshold (token counts)."""
    return f"""
    <div style="padding: 12px 14px; border-radius: 8px; border: 1px solid var(--border-color-primary);
                border-top: 3px solid {BANNER_COLORS['running']};">
        <div style="font-size: 13px; opacity: 0.8;">{label}</div>
        <div style="font-size: 26px; font-weight: 600; font-variant-numeric: tabular-nums;">{text}</div>
        <div style="font-size: 12px; opacity: 0.8;">{sub}</div>
    </div>"""


def card_grid(cards: list[str], note: str) -> str:
    joined = "".join(cards)
    return (f"<div style='display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); "
            f"gap: 12px;'>{joined}</div>"
            f"<div style='margin-top: 10px; font-size: 13px; opacity: 0.75;'>{note}</div>")


def banner(state: str, title: str, detail: str = "", pct: float | None = None) -> str:
    """One status line for the whole tab. state: idle | running | done | warn | error."""
    color = BANNER_COLORS[state]
    detail_html = f"<div style='font-size: 13px; opacity: 0.85; margin-top: 2px;'>{detail}</div>" if detail else ""
    bar_html = ""
    if pct is not None:
        bar_html = (f"<div style='height: 6px; border-radius: 3px; margin-top: 10px; overflow: hidden; "
                    f"background: var(--border-color-primary);'>"
                    f"<div style='height: 100%; width: {pct * 100:.0f}%; background: {color}; "
                    f"transition: width 0.2s ease-out;'></div></div>")
    return (f"<div role='status' aria-live='polite' style='padding: 12px 16px; border-radius: 8px; "
            f"border: 1px solid var(--border-color-primary); border-left: 4px solid {color};'>"
            f"<div style='font-weight: 600; color: {color};'>{title}</div>{detail_html}{bar_html}</div>")


def average(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def settings_text(run: dict) -> str:
    c = run.get("config", {})
    if run["pipeline"] == "baseline":
        return f"no retrieval · {c.get('answer_model', '?')}"
    if run["pipeline"] == "rag_pro":
        on_off = lambda flag: "on" if c.get(flag) else "off"
        return (f"LLM chunks · rewrite {on_off('query_rewrite')} · rerank {on_off('rerank')} · "
                f"k={c.get('final_k')} · {c.get('embedding_model')} · {c.get('answer_model')}")
    return (f"{c.get('chunk_size')}/{c.get('chunk_overlap')} · {c.get('embedding_model')} · "
            f"k={c.get('retrieval_k')} · {c.get('answer_model')}")


def run_header(run: dict) -> str:
    return (f"**{run.get('label', run['name'])}** · {run['pipeline']} · {run['created'].replace('T', ' ')}<br>"
            f"Settings: {settings_text(run)} · judge: {run.get('config', {}).get('judge_model', '?')}")


# ---------- rendering one run (fresh or saved, same code) ----------
# Each view returns (section_visibility, cards, chart, table). A section with nothing
# to show is hidden instead of drawn empty, so there is never an empty chart or spinner.

def _hidden(chart: pd.DataFrame):
    return gr.update(visible=False), PLACEHOLDER, chart, pd.DataFrame()


def retrieval_view(run: dict | None):
    empty_chart = pd.DataFrame({"Category": [], "Source MRR": []})
    if not run or not run.get("retrieval"):
        return _hidden(empty_chart)

    overall = run["retrieval"]["overall"]
    questions = run["retrieval"]["questions"]
    cards = card_grid([
        metric_card("Source MRR (first correct page)", overall["source_mrr"], "fraction"),
        metric_card("nDCG (all correct pages)", overall["ndcg"], "fraction"),
        metric_card("Keyword MRR", overall["keyword_mrr"], "fraction"),
        metric_card("Page coverage", overall["page_coverage"], "fraction"),
        metric_card("Keyword coverage", overall["keyword_coverage"], "fraction"),
    ], f"Evaluated {len(questions)} questions (questions with nothing to retrieve are skipped).")

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
    return gr.update(visible=True), cards, chart, table


def answer_view(run: dict | None):
    empty_chart = pd.DataFrame({"Category": [], "Accuracy": []})
    if not run or not run.get("answers"):
        return _hidden(empty_chart)

    overall = run["answers"]["overall"]
    questions = run["answers"]["questions"]
    tokens = run["answers"].get("tokens")
    card_list = [
        metric_card("Accuracy", overall["accuracy"], "score"),
        metric_card("Completeness", overall["completeness"], "score"),
        metric_card("Relevance", overall["relevance"], "score"),
    ]
    note = f"Judged {len(questions)} answers."
    if tokens:
        card_list.append(info_card("Avg tokens per question", f"{tokens['avg_total']:,.0f}",
                                   f"{tokens['avg_prompt']:,.0f} in · {tokens['avg_completion']:,.0f} out"))
    else:
        note += " No token data: this run was saved before token tracking."
    cards = card_grid(card_list, note)

    by_category = defaultdict(list)
    for q in questions:
        by_category[q["category"]].append(q["accuracy"])
    chart = pd.DataFrame([{"Category": c, "Accuracy": average(v)} for c, v in by_category.items()])

    table = pd.DataFrame([
        {"ID": q["id"], "Category": q["category"], "Type": q["type"], "Accuracy": q["accuracy"],
         "Completeness": q["completeness"], "Relevance": q["relevance"], "Tokens": q.get("total_tokens"),
         "Judge feedback": q["feedback"], "Answer": q["answer"]}
        for q in questions
    ]).sort_values(["Accuracy", "Completeness"])
    return gr.update(visible=True), cards, chart, table


# ---------- tab 1: run evaluation ----------
# Output order for every Run-tab event:
#   status banner, current run (State), retrieval x4, answers x4, save box, save status, 2 buttons

N_RUN_OUTPUTS = 14


def run_frame(status: str, run: dict | None = None, running: bool = False, pipeline: str = "rag"):
    """A complete UI state: banner, results, save box and buttons all agree with each other."""
    finished = run is not None and not running
    return (status, run, *retrieval_view(run), *answer_view(run),
            gr.update(visible=finished), "",
            gr.update(interactive=not running and pipeline != "baseline"),
            gr.update(interactive=not running))


def progress_frame(step: str, detail: str, pct: float):
    """Only the banner changes while running; every other output is left alone."""
    return (banner("running", f"{step} · {pct:.0%}", detail, pct), *[gr.skip()] * (N_RUN_OUTPUTS - 1))


def run_eval(pipeline_label: str, with_answers: bool, rewrite: bool = False, rerank: bool = False):
    pipeline = PIPELINES[pipeline_label]
    # rag_pro reads its flags on every question, so setting them here applies to this run
    # (and run_config saves them with it)
    pro_config.USE_QUERY_REWRITE, pro_config.USE_RERANK = rewrite, rerank
    if pipeline == "baseline" and not with_answers:
        yield run_frame(banner("warn", "The baseline has no retrieval step to score",
                               "It puts every page in the prompt. Use Full evaluation to score its answers."),
                        None, pipeline=pipeline)
        return

    try:
        yield run_frame(banner("running", "Starting", "Loading the pipeline", 0.0), None, True, pipeline)

        retrieval, answer_start = None, 0.0
        if pipeline != "baseline":
            retrieval = []
            answer_start = 0.2 if with_answers else 1.0
            uses_llm = pipeline == "rag_pro" and (rewrite or rerank)
            for test, result, prog in evaluate_all_retrieval(get_fetch_fn(pipeline)):
                yield progress_frame("Retrieval", f"{test.id} · {'rewrite/rerank LLM calls' if uses_llm else 'no LLM calls'}",
                                     prog * answer_start)
                if result is not None:
                    retrieval.append((test, result))

        answers = None
        if with_answers:
            answers = []
            for test, result, answer, tokens, prog in evaluate_all_answers(get_answer_fn(pipeline)):
                yield progress_frame("Judging answers", f"{test.id} · LLM calls, slower",
                                     answer_start + prog * (1 - answer_start))
                answers.append((test, result, answer, tokens))

        run = make_run("unsaved", pipeline, run_config(pipeline), retrieval, answers)
    except Exception as err:
        yield run_frame(banner("error", "Evaluation failed",
                               f"{type(err).__name__}: {html.escape(str(err))}. See the terminal for details, then run again."),
                        None, pipeline=pipeline)
        return

    yield run_frame(banner("done", "Finished, not saved yet",
                           "Review the results below. To keep this run, name it and click Save run."),
                    run, pipeline=pipeline)


def run_retrieval_only(pipeline_label: str, rewrite: bool, rerank: bool):
    yield from run_eval(pipeline_label, False, rewrite, rerank)


def run_full(pipeline_label: str, rewrite: bool, rerank: bool):
    yield from run_eval(pipeline_label, True, rewrite, rerank)


def save_current_run(run: dict | None, name: str):
    """Save the run held in memory under the given name."""
    name = name.strip()
    if not run:
        return banner("warn", "Nothing to save", "Run an evaluation first.")
    if not name:
        return banner("warn", "Give the run a name", "Type a short name such as rag-v1, then click Save run.")
    path = save_run({**run, "name": name})
    return banner("done", f"Saved as {html.escape(name)}",
                  f"File: results/runs/{path.name}. It now shows in Saved run, Progress and Compare.")


# ---------- tab 2: saved run ----------

def find_run(label: str | None) -> dict | None:
    return next((r for r in load_runs() if r["label"] == label), None) if label else None


def show_saved_run(label: str | None):
    run = find_run(label)
    if run:
        header = run_header(run)
    elif load_runs():
        header = "Pick a saved run above."
    else:
        header = "No saved runs yet. Run an evaluation on the first tab, then save it."
    return (header, *retrieval_view(run), *answer_view(run))


# ---------- tab 3: progress ----------

def progress_view():
    runs = load_runs()
    if not runs:
        empty = pd.DataFrame({"Run": [], "Value": [], "Pipeline": []})
        return "No saved runs yet. Run an evaluation and save it to start the chart.", pd.DataFrame(), empty, empty, empty, empty

    rows = []
    for run in runs:
        row = {"Run": run["label"], "Pipeline": run["pipeline"], "Date": run["created"][:16].replace("T", " ")}
        for m in ANSWER_METRICS:
            row[METRIC_NAMES[m]] = run["answers"]["overall"][m] if run.get("answers") else None
        row["Avg tokens"] = ((run.get("answers") or {}).get("tokens") or {}).get("avg_total")
        for m in ["source_mrr", "ndcg", "page_coverage"]:
            row[METRIC_NAMES[m]] = run["retrieval"]["overall"][m] if run.get("retrieval") else None
        row["Settings"] = settings_text(run)
        rows.append(row)
    table = pd.DataFrame(rows)

    def chart(metric_col: str) -> pd.DataFrame:
        df = table[["Run", metric_col, "Pipeline"]].dropna().rename(columns={metric_col: "Value"})
        return df

    note = f"{len(runs)} saved runs, oldest first. Each bar is one version of the system."
    return note, table, chart("Accuracy"), chart("Avg tokens"), chart("Source MRR"), chart("nDCG")


# ---------- tab 4: compare ----------

def compare_runs(label_a: str | None, label_b: str | None):
    run_a, run_b = find_run(label_a), find_run(label_b)
    if not run_a or not run_b:
        return "Pick two saved runs.", pd.DataFrame()

    lines = [f"**A:** {run_a['label']} ({settings_text(run_a)})<br>**B:** {run_b['label']} ({settings_text(run_b)})", ""]
    lines.append("| Metric | A | B | Change |")
    lines.append("|---|---|---|---|")
    for section, metrics in [("answers", ANSWER_METRICS), ("retrieval", RETRIEVAL_METRICS)]:
        if run_a.get(section) and run_b.get(section):
            for m in metrics:
                a, b = run_a[section]["overall"][m], run_b[section]["overall"][m]
                lines.append(f"| {METRIC_NAMES[m]} | {a:.2f} | {b:.2f} | {b - a:+.2f} |")

    if len(lines) == 4:   # still just the header rows: the runs share no scored section
        return ("These two runs have no scored section in common (for example one is retrieval-only and "
                "the other answers-only). Re-run both with **Full evaluation** and save them again."), pd.DataFrame()

    tok_a = (run_a.get("answers") or {}).get("tokens")
    tok_b = (run_b.get("answers") or {}).get("tokens")
    if tok_a and tok_b and tok_a["avg_total"] and tok_b["avg_total"]:
        a, b = tok_a["avg_total"], tok_b["avg_total"]
        lines.append(f"| Avg tokens per question (lower is cheaper) | {a:,.0f} | {b:,.0f} | {b / a - 1:+.0%} |")
        lines.append("")
        lines.append(f"**B uses {a / b:.1f}x fewer tokens than A.**" if b < a
                     else f"**B uses {b / a:.1f}x more tokens than A.**")

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

def retrieval_block():
    """Hidden until there is a retrieval result. Returns [section, cards, chart, table]."""
    with gr.Column(visible=False) as section:
        gr.Markdown("### Retrieval")
        gr.Markdown("How well the search step finds the right pages. RAG only, free, no LLM calls.")
        cards = gr.HTML(PLACEHOLDER)
        chart = gr.BarPlot(x="Category", y="Source MRR", title="Source MRR by category",
                           y_lim=[0, 1], height=300, sort="y")
        table = gr.Dataframe(label="Per question (worst first)", wrap=True)
    return [section, cards, chart, table]


def answer_block():
    """Hidden until there is an answer result. Returns [section, cards, chart, table]."""
    with gr.Column(visible=False) as section:
        gr.Markdown("### Answers")
        gr.Markdown("An LLM judge scores each answer from 1 to 5.")
        cards = gr.HTML(PLACEHOLDER)
        chart = gr.BarPlot(x="Category", y="Accuracy", title="Accuracy by category",
                           y_lim=[1, 5], height=300, sort="y")
        table = gr.Dataframe(label="Per question (worst first)", wrap=True)
    return [section, cards, chart, table]


def progress_chart(title: str, y_lim: list[float] | None = None):
    return gr.BarPlot(x="Run", y="Value", color="Pipeline", color_map=PIPELINE_COLORS,
                      title=title, y_lim=y_lim, height=320, x_label_angle=-30, sort="x")


def main():
    with gr.Blocks(title="MSME RAG Evaluation") as app:
        gr.Markdown("# MSME RAG Evaluation")
        gr.Markdown("Retrieval and answer quality for the Sri Lankan MSME loan assistant. "
                    "Same 33 questions and the same judge for every run.")

        with gr.Tab("Run evaluation"):
            current_run = gr.State(None)

            gr.Markdown("#### 1. Choose a system")
            pipeline = gr.Radio(list(PIPELINES), value="RAG", label="System to evaluate",
                                info="RAG searches fixed-size chunks. RAG Pro searches LLM-made chunks. "
                                     "Baseline puts every page in the prompt.")
            with gr.Row(visible=False) as pro_options:
                pro_rewrite = gr.Checkbox(pro_config.USE_QUERY_REWRITE, label="Query rewriting",
                                          info="+1 LLM call per question: also searches with a rewritten query")
                pro_rerank = gr.Checkbox(pro_config.USE_RERANK, label="Reranking",
                                         info="+1 LLM call per question: LLM sorts 20 candidates, keeps the best 10")

            gr.Markdown("#### 2. Run")
            with gr.Row():
                retrieval_button = gr.Button(RETRIEVAL_LABEL)
                full_button = gr.Button("Full evaluation (retrieval + answers, ~66 LLM calls)", variant="primary")
            run_status = gr.HTML(banner("idle", "Ready", "Pick a system and run an evaluation. Results appear below."))

            with gr.Column(visible=False) as save_box:
                gr.Markdown("#### 3. Save this run (optional)")
                with gr.Row(equal_height=True):
                    save_name = gr.Textbox(label="Run name", scale=3,
                                           info="Saved runs feed the Progress and Compare tabs.",
                                           placeholder="e.g. rag-v1, rag-pro-rerank, baseline")
                    save_button = gr.Button("Save run", scale=1)
                save_status = gr.HTML("")

            run_retrieval = retrieval_block()
            run_answers = answer_block()

        with gr.Tab("Saved run"):
            saved_pick = gr.Dropdown(label="Saved run", choices=[])
            saved_header = gr.Markdown()
            saved_outputs = retrieval_block() + answer_block()

        with gr.Tab("Progress"):
            progress_refresh = gr.Button("Refresh")
            progress_note = gr.Markdown()
            with gr.Row():
                progress_accuracy = progress_chart("Answer accuracy (1-5)", [1, 5])
                progress_tokens = progress_chart("Avg tokens per question (lower is cheaper)")
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
        progress_outputs = [progress_note, progress_table, progress_accuracy, progress_tokens,
                            progress_mrr, progress_ndcg]
        run_outputs = [run_status, current_run, *run_retrieval, *run_answers,
                       save_box, save_status, retrieval_button, full_button]

        # The banner is the one source of progress feedback, so Gradio's own overlay is hidden.
        run_inputs = [pipeline, pro_rewrite, pro_rerank]
        retrieval_button.click(run_retrieval_only, inputs=run_inputs, outputs=run_outputs, show_progress="hidden")
        full_button.click(run_full, inputs=run_inputs, outputs=run_outputs, show_progress="hidden")
        pipeline.change(
            lambda p: (gr.update(interactive=p != "Baseline",
                                 value=RETRIEVAL_LABEL if p != "Baseline" else "Retrieval only (not available for Baseline)"),
                       gr.update(visible=p == "RAG Pro")),
            inputs=pipeline, outputs=[retrieval_button, pro_options], show_progress="hidden")

        gr.on(
            triggers=[save_button.click, save_name.submit],
            fn=save_current_run, inputs=[current_run, save_name], outputs=save_status, show_progress="hidden",
        ).then(refresh_choices, outputs=dropdowns, show_progress="hidden"
        ).then(progress_view, outputs=progress_outputs, show_progress="hidden")

        saved_pick.change(show_saved_run, inputs=saved_pick, outputs=[saved_header, *saved_outputs])
        progress_refresh.click(progress_view, outputs=progress_outputs).then(refresh_choices, outputs=dropdowns)
        compare_button.click(compare_runs, inputs=[compare_a, compare_b], outputs=[compare_summary, compare_table])

        app.load(progress_view, outputs=progress_outputs).then(refresh_choices, outputs=dropdowns)

    app.launch(inbrowser=True, theme=THEME)


if __name__ == "__main__":
    main()
