"""Counts the LLM tokens spent producing one answer.

Every LLM call inside a pipeline (the answer call today; query rewriting, reranking etc. in v2)
calls record() once. The eval calls reset() before a question and snapshot() after it, so the
total covers the whole pipeline without answer_question having to return anything extra.
The judge's own tokens are not counted: they are the cost of testing, not of answering.
"""

_calls: list[tuple[int, int]] = []


def reset() -> None:
    _calls.clear()


def record(prompt_tokens: int | None, completion_tokens: int | None) -> None:
    _calls.append((prompt_tokens or 0, completion_tokens or 0))


def snapshot() -> dict:
    prompt = sum(p for p, _ in _calls)
    completion = sum(c for _, c in _calls)
    return {"prompt_tokens": prompt, "completion_tokens": completion,
            "total_tokens": prompt + completion, "calls": len(_calls)}
