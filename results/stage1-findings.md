# Stage 1 baseline findings (brute-force, no RAG)

Ran `baseline.py` (full-document dump into context, no chunking/retrieval)
against a sample of questions from `eval/questions.md`. Logged 2026-10-22.

## Questions tested
Q02, Q07, Q08, Q23, Q28, Q29, Q32

## Findings

### 1. Citation page numbers sometimes wrong even when content is correct
Q02 content was correct (turnover < Rs. 1,000M, employees < 200), but cited
FAQ pages 2 and 4, and GL page 4. Expected sources are FAQ p1 and GL p3.
Citation accuracy cannot be trusted even when the answer text itself is right.

### 2. Systematic conflation of SMELoC/SMELOC2 with Component I/II (root cause found)
Q07 (max loan amounts): correctly gave SMELoC = Rs. 50M, but then said
"SMELOC2's maximum loan amount is Rs. 15 million for Component I ... and
Rs. 5 million for Component II." This is wrong — SMELOC2 is a separate ADB
scheme with its own Rs. 10M limit, unrelated to Component I/II of the
Re-energizing MSME scheme (a different, GoSL-funded program). The real
SMELOC2 figure (10M) never appeared.

Q23 (SMELoC vs SMELOC2 comparison) repeated the same error, confirming it's
systematic, not a one-off: again attributed Component I/II loan amounts to
SMELOC2, and additionally claimed "SMELoC ... maximum repayment period of 10
years" — wrong, SMELoC's real repayment period is 5 years; 10 years is
actually Component I's figure.

Likely root cause: in the extracted text of `treasury_msme_loan_schemes_summary.pdf`,
the table's real header row (naming which column is SMELoC vs SMELOC2) was
relocated by `pypdf` to the bottom of page 1, after all the data rows, while
the "Component I / Component II" labels appear at the very top of the page,
looking like they belong to the same section. This column/header
misalignment in plain-text extraction is causing the model to cross-wire
facts between the two unrelated scheme groups (SMELoC/SMELOC2 vs Component
I/II).

Action for Stage 2: this table needs special handling (don't rely on plain
`extract_text()` for it) — consider extracting it as structured rows
(e.g. a table-aware PDF parser, or manually transcribing this one 2-page
table given how small it is) rather than trusting flat text extraction.

### 3. Incomplete coverage on multi-scheme questions
Q08 (max interest rate "for each scheme") only answered for SMELoC and
SMELOC2, omitting Component I (7%) and Component II (8%) entirely, despite
the question asking about all schemes.

### 4. Hard rule violation: asserted a time-sensitive scheme was "still open"
Q28 correctly extracted the scheme's date range (2 May 2024 - 1 May 2026,
cited GL page 14; expected page 13, off by one - check indexing) but then
concluded "the scheme is still open for applications during this period."
The expected behavior explicitly forbids this — it must hedge and point the
user to confirm with the Department of Development Finance or a bank.

Root cause: the system prompt never tells the model today's date, so it has
no way to reason about whether 1 May 2026 has already passed. Today's real
date (2026-10-22) is in fact after the scheme's stated termination date.

Action for Stage 2/4: inject the current date into the prompt/context for
any time-sensitive reasoning. This is a prerequisite for the
"version-aware RAG" work in Stage 4, not just a prompt tweak.

### 5. Refusal behavior works, but is thin
Q29 (bank-specific interest rate) and Q32 (scheme not in the documents)
asked together, correctly answered "I don't know. Please check with the
bank." No hallucination. However, it didn't explain *why* it doesn't know
(i.e. "this isn't covered in the provided documents") the way the expected
answers do - worth tightening the prompt to ask for a brief reason, not just
a bare refusal.

## Summary
Baseline (no RAG) gets simple, single-fact questions right but:
- cites inconsistent page numbers even for correct answers
- systematically confuses two unrelated scheme groups whenever the table's
  scrambled structure is involved (loan amounts, repayment periods)
- misses schemes when a question implicitly expects all of them covered
- fails a hard safety rule on time-sensitive questions due to not knowing
  today's date
- refuses appropriately on out-of-scope questions, but without justification

These are the numbers/behaviors RAG (Stage 2) and version-aware RAG (Stage 4)
need to improve on. Re-run this same question set once Stage 2 is built for
a before/after comparison.
