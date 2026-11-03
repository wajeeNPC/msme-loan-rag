PROJECT: Sri Lanka MSME Loan Assistant (RAG)

--------------------------------------------------
ONE-LINER
An AI assistant that helps Sri Lankan MSME owners understand government
SME loan eligibility, limits, documents, repayment terms and application
steps, using only official documents and showing citations.

--------------------------------------------------
THE PROBLEM
Small business owners want government-backed loans but can't tell which
scheme they qualify for, how much they can borrow, which documents they
need, or how to apply. The information exists, but it is spread across
official FAQ pages, PDF guidelines, tables and bank-specific rules. So
people keep asking bank officers the same questions, or give up.

--------------------------------------------------
WHO HAS THE PROBLEM
- A small manufacturer wondering if they qualify for a Rs. 15M loan
- A startup that hasn't finished business registration
- A tourism or agriculture business comparing SMELoC vs SMELOC2
- A business owner with a past non-performing loan asking about relief funding
- A bank front-desk officer answering the same eligibility/document questions

--------------------------------------------------
WHY IT'S PAINFUL (examples from the Treasury MSME FAQ — re-verify each
against the source before using it in the app or case study)
- Max loan differs by scheme (SMELoC vs SMELOC2)
- Re-energizing MSME scheme has two components (existing/startup vs NPL)
- Trading, leasing and renting businesses are excluded
- Registration is generally required; startups may submit an application instead
- Repayment and grace periods differ by scheme
Source: treasury.gov.lk -> FAQ -> MSME loans

--------------------------------------------------
WHAT THE PRODUCT DOES
User asks in plain language, e.g.:
"I run a small garment factory with 30 employees and Rs. 40M annual
turnover. Can I get a government SME loan, and what documents do I need?"

Assistant answers with:
- Whether they meet the general eligibility rules
- Which schemes may fit
- Max loan amount and interest-rate cap
- Required documents
- Where to apply
- Citations (e.g. "Treasury MSME FAQ", "guideline.pdf, page 4")

If the documents don't contain the answer -> says "I don't know, please
check with the bank" instead of guessing.

--------------------------------------------------
RULES FOR THE ASSISTANT
- Answer ONLY from the indexed official documents
- Every claim needs a citation (document + page)
- Unclear or missing info -> say so, never guess
- Always show a disclaimer: "Not financial advice, confirm with the bank"
- Say which version/date of the document the answer is based on

--------------------------------------------------
V1 SCOPE (keep it small)
- 2-3 schemes, 1-2 banks
- Official FAQ page + 2-3 PDF guidelines
- Questions on: eligibility, loan limits, documents, repayment, how to apply
- OUT of scope for V1: Sinhala/Tamil, eligibility calculator, all banks

--------------------------------------------------
BUILD PLAN
Stage 0  Collect docs + write 20-30 real test questions
         (from the examples above and from a bank officer / business owner)
Stage 1  Baseline: PDF text -> prompt -> answer (before RAG week)
Stage 2  Real RAG: chunking, embeddings, vector DB, top-k retrieval,
         citations with page numbers. Handle tables carefully.
Stage 3  Evals: retrieval hit rate, answer correctness, citation accuracy,
         "I don't know" behavior on out-of-scope questions
Stage 4  Version-aware RAG: document version + date metadata, prefer the
         newest, flag conflicts between versions
Stage 5  Ship: deploy, 60-sec demo video, case study with eval results

--------------------------------------------------
SUCCESS CHECKS
[ ] Gives correct answers on my test set, with the right citation
[ ] Says "I don't know" when the docs don't cover it
[ ] Cites document + page every time
[ ] One real person (business owner or bank officer) has tried it
[ ] Case study: problem -> approach -> eval numbers -> what I'd improve

--------------------------------------------------
RISKS
- Scheme rules change -> track document versions and dates
- Wrong eligibility answer could mislead someone -> disclaimer + refusal on low confidence
- Tables in PDFs are hard to parse -> test extraction early
- Bank-specific rules may not be public -> check before promising them

--------------------------------------------------
PORTFOLIO LINE
"Built a citation-backed RAG assistant for Sri Lankan government SME loan
schemes, evaluated on a real-world question set, with version-aware
retrieval and refusal on unsupported questions."