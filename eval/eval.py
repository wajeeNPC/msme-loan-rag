import os
import sys
import math
from collections import defaultdict
from pydantic import BaseModel , Field
from litellm import completion
from dotenv import load_dotenv

from eval.test import TestQuestion , load_tests , Source
from rag.answer import answer_question , fetch_context
from rag import config as rag_config
from rag import usage
from eval.runs import make_run, save_run
from langchain_core.documents import Document

load_dotenv(override=True)

JUDGE_MODEL = "openrouter/openai/gpt-4.1"

class RetrivalEval(BaseModel):
    """Evaluation metric for retrival performance"""

    keyword_mrr : float = Field(description="Keyword MRR - average of calculate_keyword_mrr over all keywords")
    source_mrr : float  = Field(description="Source MRR - rank of first chunk matching an expected (file, page)")
    ndcg : float = Field(description="nDCG over expected (file, page) sources (binary relevance)")
    keywords_found : int = Field(description="Number of keywords found in top-k results")
    file_found : int = Field(description="Number of files found in top-k results")
    total_keywords: int = Field(description="Total number of keywords to find")
    total_files: int = Field(description="Total number of files to find")
    keyword_coverage: float = Field(description="Fraction (0-1) of keywords found")
    files_coverage: float = Field(description="Fraction (0-1) of files found")
    pages_found: int = Field(description="Expected (file, page) pairs found in top-k results")
    total_pages: int = Field(description="Total expected (file, page) pairs")
    page_coverage: float = Field(description="Fraction (0-1) of expected pages found")

def source_matches(doc : Document , src : Source ) -> bool :
    file_name = os.path.basename(doc.metadata.get("source" , ""))
    if file_name != src.file :
        return False

    page = doc.metadata.get("page")
    if page is None:
        return False
    return page + 1 == src.page

class AnswerEval(BaseModel) :
    """LLM-as-a-judge evaluation of answer quality."""

    feedback : str = Field( description="Concise feedback on the answer quality, comparing it to the reference answer and evaluating based on the retrieved context")
    accuracy: float = Field( description="How factually correct is the answer compared to the reference answer? 1 (wrong. any wrong answer must score 1) to 5 (ideal - perfectly accurate). An acceptable answer would score 3.")
    completeness: float = Field( description="How complete is the answer in addressing all aspects of the question? 1 (very poor - missing key information) to 5 (ideal - all the information from the reference answer is provided completely). Only answer 5 if ALL information from the reference answer is included.")
    relevance: float = Field( description="How relevant is the answer to the specific question asked? 1 (very poor - off-topic) to 5 (ideal - directly addresses question and gives no additional information). Only answer 5 if the answer is completely relevant to the question and gives no additional information.")


def calculate_keyword_mrr(keyword : str , docs : list[Document] ) -> float :
    keyword_lower = keyword.lower()
    for rank , doc in enumerate(docs , start=1 ):
        if keyword_lower in doc.page_content.lower():
            return 1 / rank
    return 0

def calculate_source_mrr( docs : list[Document] , expected : list[Source] ) -> float :
    for rank , doc in enumerate(docs , start = 1 ):
        if any(source_matches(doc, src) for src in expected):
            return 1 / rank
    return 0

def calculate_dcg(relevances: list[int]) -> float:
    total = 0.0
    for rank, rel in enumerate(relevances, start=1):
        total += rel / math.log2(rank+1)
    return total

def calculate_ndcg(docs: list[Document], expected: list[Source]) -> float:
    relevances = [1 if any(source_matches(doc, src) for src in expected) else 0
                  for doc in docs]

    dcg = calculate_dcg(relevances)
    ideal = sorted(relevances, reverse=True)
    idcg = calculate_dcg(ideal)

    if idcg == 0:
        return 0
    return dcg / idcg


def fraction(found: int, total: int) -> float:
    return found / total if total else 0.0


def evaluate_retrieval(test: TestQuestion) -> RetrivalEval | None:
    """Score retrieval for one question. Returns None when there is nothing to find
    (questions like Q29/Q32/Q33 with no keywords and no expected sources)."""
    if not test.keywords and not test.expected_sources:
        return None

    docs = fetch_context(test.question)

    # Keywords: one MRR per keyword, then average
    keyword_scores = [calculate_keyword_mrr(kw, docs) for kw in test.keywords]
    keywords_found = sum(1 for score in keyword_scores if score > 0)

    # Files: unique expected file names, found if any retrieved chunk comes from that file
    retrieved_files = {os.path.basename(doc.metadata.get("source", "")) for doc in docs}
    expected_files = {src.file for src in test.expected_sources}
    files_found = len(expected_files & retrieved_files)

    # Pages: each expected (file, page) pair, found if any chunk matches it
    pages_found = sum(1 for src in test.expected_sources
                      if any(source_matches(doc, src) for doc in docs))

    return RetrivalEval(
        keyword_mrr=fraction(sum(keyword_scores), len(keyword_scores)),
        source_mrr=calculate_source_mrr(docs, test.expected_sources),
        ndcg=calculate_ndcg(docs, test.expected_sources),
        keywords_found=keywords_found,
        total_keywords=len(test.keywords),
        keyword_coverage=fraction(keywords_found, len(test.keywords)),
        file_found=files_found,
        total_files=len(expected_files),
        files_coverage=fraction(files_found, len(expected_files)),
        pages_found=pages_found,
        total_pages=len(test.expected_sources),
        page_coverage=fraction(pages_found, len(test.expected_sources)),
    )


JUDGE_SYSTEM = """You are an expert evaluator for a Sri Lankan MSME government-loan assistant.
Compare the generated answer to the reference answer. Only give 5/5 for perfect answers.
Some questions are ones the assistant should NOT answer confidently (type "idk"): the documents
don't cover them, or the honest answer is "I don't know / check with the bank". For those, a
correct answer declines or hedges as the reference describes; inventing specifics (a bank's rate,
a guarantee of approval, a scheme not in the documents) is wrong and must score accuracy 1."""


def evaluate_answer(test: TestQuestion, answer_fn=answer_question) -> tuple[AnswerEval, str, list[Document], dict]:
    """Get an answer from answer_fn (RAG by default, or the baseline), then have an LLM grade it.
    answer_fn(question, history) must return (answer_text, docs). The last item returned is the
    tokens spent producing the answer (collected by rag.usage; the judge's tokens are not counted)."""
    usage.reset()
    generated_answer, docs = answer_fn(test.question, [])
    tokens = usage.snapshot()

    user_prompt = f"""Question type: {test.type}

Question:
{test.question}

Generated Answer:
{generated_answer}

Reference Answer:
{test.reference_answer}

Evaluate the generated answer on:
1. Accuracy: factually correct compared to the reference? If it is wrong, accuracy must be 1.
2. Completeness: covers all the information in the reference answer?
3. Relevance: directly answers the question without unrelated extra information?

Give concise feedback and a score from 1 (very poor) to 5 (ideal) for each."""

    response = completion(
        model=JUDGE_MODEL,
        messages=[
            {"role": "system", "content": JUDGE_SYSTEM},
            {"role": "user", "content": user_prompt},
        ],
        response_format=AnswerEval,
    )
    answer_eval = AnswerEval.model_validate_json(response.choices[0].message.content)
    return answer_eval, generated_answer, docs, tokens


def average(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def run_retrieval_eval(tests: list[TestQuestion]) -> list[tuple[TestQuestion, RetrivalEval]]:
    """Retrieval metrics for every question, grouped by category. No LLM calls, so it's free.
    Returns (test, result) pairs so the run can be saved."""
    by_category = defaultdict(list)
    scored = []
    skipped = []
    print(f"\n{'ID':<5} {'Category':<20} {'kwMRR':>6} {'srcMRR':>7} {'nDCG':>6} {'kw':>6} {'pages':>6}")
    for test in tests:
        result = evaluate_retrieval(test)
        if result is None:
            skipped.append(test.id)
            continue
        by_category[test.category].append(result)
        scored.append((test, result))
        print(f"{test.id:<5} {test.category:<20} {result.keyword_mrr:>6.2f} {result.source_mrr:>7.2f} "
              f"{result.ndcg:>6.2f} {result.keywords_found:>3}/{result.total_keywords:<2} "
              f"{result.pages_found:>3}/{result.total_pages:<2}")

    print(f"\n{'Category':<20} {'n':>3} {'kwMRR':>6} {'srcMRR':>7} {'nDCG':>6} {'kwCov':>6} {'pgCov':>6}")
    all_results = [r for results in by_category.values() for r in results]
    for category, results in [*by_category.items(), ("OVERALL", all_results)]:
        print(f"{category:<20} {len(results):>3} "
              f"{average([r.keyword_mrr for r in results]):>6.2f} "
              f"{average([r.source_mrr for r in results]):>7.2f} "
              f"{average([r.ndcg for r in results]):>6.2f} "
              f"{average([r.keyword_coverage for r in results]):>6.2f} "
              f"{average([r.page_coverage for r in results]):>6.2f}")
    if skipped:
        print(f"\nSkipped (nothing to retrieve): {', '.join(skipped)}")
    return scored


def run_answer_eval(tests: list[TestQuestion], answer_fn=answer_question) -> list[tuple[TestQuestion, AnswerEval, str, dict]]:
    """LLM-judge every question. Costs 2 LLM calls per question (answer + judge).
    Returns (test, judge result, generated answer, tokens) so the run can be saved."""
    by_category = defaultdict(list)
    scored = []
    print(f"\n{'ID':<5} {'Category':<20} {'Acc':>4} {'Comp':>5} {'Rel':>4} {'Tokens':>8}")
    for test in tests:
        result, generated_answer, _, tokens = evaluate_answer(test, answer_fn)
        by_category[test.category].append(result)
        scored.append((test, result, generated_answer, tokens))
        print(f"{test.id:<5} {test.category:<20} {result.accuracy:>4.1f} {result.completeness:>5.1f} {result.relevance:>4.1f} "
              f"{tokens['total_tokens']:>8,}")

    print(f"\n{'Category':<20} {'n':>3} {'Acc':>5} {'Comp':>5} {'Rel':>5}")
    all_results = [r for results in by_category.values() for r in results]
    for category, results in [*by_category.items(), ("OVERALL", all_results)]:
        print(f"{category:<20} {len(results):>3} "
              f"{average([r.accuracy for r in results]):>5.2f} "
              f"{average([r.completeness for r in results]):>5.2f} "
              f"{average([r.relevance for r in results]):>5.2f}")
    print(f"\nTokens per question (answer only, judge not counted): "
          f"avg {average([t['total_tokens'] for _, _, _, t in scored]):,.0f} "
          f"({average([t['prompt_tokens'] for _, _, _, t in scored]):,.0f} in, "
          f"{average([t['completion_tokens'] for _, _, _, t in scored]):,.0f} out)")
    return scored


def run_single(test: TestQuestion, answer_fn=answer_question, with_retrieval: bool = True) -> None:
    """Full detail for one question: retrieval metrics (RAG only), the generated answer, and the judge's verdict."""
    print(f"\n{'=' * 80}\n{test.id} [{test.category} / {test.type}]\n{'=' * 80}")
    print(f"Question: {test.question}")
    print(f"Keywords: {test.keywords}")
    print(f"Expected: {[f'{s.file} p{s.page}' for s in test.expected_sources]}")

    if with_retrieval:
        print(f"\n--- Retrieval ---")
        result = evaluate_retrieval(test)
        if result is None:
            print("Skipped (no keywords or expected sources)")
        else:
            print(f"Keyword MRR: {result.keyword_mrr:.2f}   Source MRR: {result.source_mrr:.2f}   nDCG: {result.ndcg:.2f}")
            print(f"Keywords {result.keywords_found}/{result.total_keywords}   "
                  f"Files {result.file_found}/{result.total_files}   Pages {result.pages_found}/{result.total_pages}")

    print(f"\n--- Answer ---")
    answer_result, generated_answer, docs, tokens = evaluate_answer(test, answer_fn)
    print(f"Tokens: {tokens['total_tokens']:,} ({tokens['prompt_tokens']:,} in, {tokens['completion_tokens']:,} out, {tokens['calls']} LLM call(s))")
    print("Retrieved:", [f"{os.path.basename(d.metadata.get('source', ''))} p{d.metadata.get('page', -1) + 1}" for d in docs])
    print(f"\n{generated_answer}")
    print(f"\nReference: {test.reference_answer}")
    print(f"\nJudge: {answer_result.feedback}")
    print(f"Accuracy {answer_result.accuracy}/5   Completeness {answer_result.completeness}/5   Relevance {answer_result.relevance}/5\n")


def evaluate_all_retrieval():
    """Generator for the dashboard: yields (test, result, progress) one question at a time.
    result is None for questions with nothing to retrieve."""
    tests = load_tests()
    for index, test in enumerate(tests):
        yield test, evaluate_retrieval(test), (index + 1) / len(tests)


def evaluate_all_answers(answer_fn=answer_question):
    """Generator for the dashboard: yields (test, AnswerEval, generated answer, tokens, progress).
    2 LLM calls per question."""
    tests = load_tests()
    for index, test in enumerate(tests):
        result, generated_answer, _, tokens = evaluate_answer(test, answer_fn)
        yield test, result, generated_answer, tokens, (index + 1) / len(tests)


def get_answer_fn(pipeline: str):
    """'rag' or 'baseline' -> the answer_question function to grade."""
    if pipeline == "baseline":
        # Imported only here: it reads every PDF page into memory on import
        from baseline.baseline import answer_question as baseline_answer
        return baseline_answer
    return answer_question


def run_config(pipeline: str) -> dict:
    """The settings a run used, saved next to its scores so you can tell runs apart later."""
    if pipeline == "baseline":
        from baseline.baseline import MODEL as baseline_model
        config = {"context": "all pages in prompt (no retrieval)", "answer_model": baseline_model}
    else:
        config = rag_config.as_dict()
    config["judge_model"] = JUDGE_MODEL
    return config


USAGE = """Usage (run from the project root):
  python -m eval.eval                       retrieval metrics for all questions (free, no LLM calls)
  python -m eval.eval --answers             also LLM-judge every answer (~2 LLM calls per question)
  python -m eval.eval Q07                   full detail for one question
  python -m eval.eval --baseline            LLM-judge the no-RAG baseline on every question
  python -m eval.eval --baseline Q07        full baseline detail for one question

Add --save "name" to any full run to keep it for the dashboard (results/runs/), e.g.
  python -m eval.eval --answers --save "rag-v1"
  python -m eval.eval --baseline --save "baseline"
(The baseline retrieves nothing, so it only gets answer scores.)"""


def main():
    tests = load_tests()
    args = sys.argv[1:]

    # Pull out --save "name" first
    save_name = None
    if "--save" in args:
        i = args.index("--save")
        if i + 1 >= len(args) or args[i + 1].startswith("--"):
            print('--save needs a name, e.g. --save "rag-v1"')
            sys.exit(1)
        save_name = args[i + 1]
        args = args[:i] + args[i + 2:]

    pipeline = "baseline" if "--baseline" in args else "rag"
    with_answers = "--answers" in args or pipeline == "baseline"
    rest = [a for a in args if a not in ("--baseline", "--answers")]
    answer_fn = get_answer_fn(pipeline)

    # One question in detail
    if len(rest) == 1 and not rest[0].startswith("--"):
        matches = [t for t in tests if t.id.lower() == rest[0].lower()]
        if not matches:
            print(f"No test with id {rest[0]}. Ids run from {tests[0].id} to {tests[-1].id}.")
            sys.exit(1)
        if save_name:
            print("(--save is ignored for single-question runs)")
        run_single(matches[0], answer_fn, with_retrieval=(pipeline == "rag"))
        return
    if rest:
        print(USAGE)
        sys.exit(1)

    # Full runs
    retrieval = run_retrieval_eval(tests) if pipeline == "rag" else None
    answers = run_answer_eval(tests, answer_fn) if with_answers else None

    if save_name:
        run = make_run(save_name, pipeline, run_config(pipeline), retrieval, answers)
        path = save_run(run)
        print(f"\nSaved run to {path}")


if __name__ == "__main__":
    main()