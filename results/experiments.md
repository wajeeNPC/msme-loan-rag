# Retrieval experiments

Rule: change one thing (settings live in `rag/config.py`), re-run `python -m rag.ingest`, then
`python -m eval.eval --answers --save "<name>"`, and log it here with *why* you tried it.
Saved runs land in `results/runs/` and show up in the dashboard (`python -m eval.dashboard`).
30 scored questions, so one question ≈ 0.03 — treat smaller changes as noise.

| # | Date | Change | Source MRR | nDCG | Keyword MRR | Page cov | Keyword cov | Notes |
|---|---|---|---|---|---|---|---|---|
| 0 | 2026-11-02 | Baseline: 1000/200 chunks, all-MiniLM-L6-v2, k=10 | 0.64 | 0.66 | 0.48 | 0.61 | 0.64 | Summary .md indexed under its own name, so 16/80 expected sources could never match |
| 1 | 2026-11-02 | Summary .md labelled as treasury_msme_loan_schemes_summary.pdf, split into page 1 (rows 1-7) / page 2 (rows 8-12) | 0.66 | 0.69 | 0.51 | 0.70 | 0.69 | Measurement fix, not a retrieval change. **This is the real baseline.** Q25 0 → 0.50. Still 0: Q15, Q28, Q30, Q31 |
