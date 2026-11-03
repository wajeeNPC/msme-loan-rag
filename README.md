# MSME Loan RAG

A citation-backed RAG assistant that answers questions about Sri Lankan government MSME loan schemes (SMELoC, SMELOC2, Re-energizing the MSME Sector) using only official documents. Every claim carries a source document and page number, and the assistant says "I don't know, please check with the bank" when the documents don't cover the question.

The project is built in stages, and each retrieval change is measured against a fixed test set before it is kept.

## Why

The rules for these schemes (maximum loan, eligibility, grace periods, required documents) are spread across FAQ pages, PDF guidelines and wide comparison tables. Small business owners can't easily tell which scheme fits them, and a confidently wrong answer about eligibility could mislead someone. So the assistant has to cite, refuse when unsure, and respect the current date (some schemes have expired).

## How it works

```
PDFs + summary table  ->  chunk  ->  embed  ->  Chroma vector store
                                                      |
question  ->  embed  ->  top-k retrieval  ->  prompt (with source+page labels, today's date)  ->  LLM answer + citations
```

- **Documents** (`data/raw/`): Treasury MSME FAQ, Re-energizing MSME operating guideline, and the MSME loan schemes summary. Origins and download dates are recorded in [`data/raw/sources.md`](data/raw/sources.md).
- **Tables:** the summary PDF is one wide comparison table that breaks naive text extraction, so it is hand-converted to `data/processed/loan_schemes_summary.md` and indexed with the original PDF's name and page labels.
- **Settings** live in one place, `rag/config.py`: chunk size/overlap, embedding model (local HuggingFace or OpenRouter), retrieval `k`, answer model. Ingest and answer both read from it so they can't drift apart.
- **Prompt rules:** answer only from the retrieved text, cite document + page for every claim, never state a specific bank's interest rate, include a "not financial advice" disclaimer, and compare scheme deadlines with today's date.

## Evaluation

The test set is 33 questions in `eval/tests.jsonl`: answerable questions with reference answers, expected keywords and expected source pages, plus "I don't know" questions the system should refuse.

- **Retrieval metrics:** source MRR, keyword MRR, nDCG, page coverage, keyword coverage.
- **Answer metrics:** LLM-as-judge scoring against the reference answer.
- **Experiments** are logged in [`results/experiments.md`](results/experiments.md), and each saved run records the config it used.
- **Baseline** (no RAG, documents pasted into the prompt) is scored with the same harness, for comparison.

## Project layout

```
baseline/   no-RAG baseline
rag/        config.py, ingest.py (PDF -> Chroma), answer.py (retrieval + answering, Gradio chat)
eval/       eval.py (CLI), runs.py (save/load runs), dashboard.py (Gradio), tests.jsonl, questions.md
data/       raw official PDFs, processed table markdown
results/    experiments log, stage 1 findings, saved runs
```

## Run it

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/).

```bash
uv sync
```

Create a `.env` file with your OpenRouter key (used for the LLM, the judge and, optionally, embeddings):

```
OPENROUTER_API_KEY=your-key
```

Build the vector store, then chat:

```bash
uv run python -m rag.ingest
uv run python -m rag.answer
```

Run the evaluation:

```bash
uv run python -m eval.eval                     # retrieval metrics, all questions
uv run python -m eval.eval --answers           # plus answer scoring
uv run python -m eval.eval --answers --save "my-experiment"
uv run python -m eval.eval Q07                 # a single question
uv run python -m eval.eval --baseline          # score the no-RAG baseline
uv run python -m eval.dashboard                # compare saved runs
```

If you change the chunking or embedding settings in `rag/config.py`, re-run `rag.ingest` first, because vectors from different embedding models can't be searched together.

## Limitations

- Scheme rules and rates change, and the documents here are snapshots (see download dates in `sources.md`).
- Only three documents are indexed so far. The SMELoC and SMELOC2 operating guidelines and bank-specific rules are missing.
- English only (Sinhala and Tamil are out of scope for v1).
- Not financial advice. Always confirm with the Department of Development Finance or your bank.
