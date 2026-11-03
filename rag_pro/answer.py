"""RAG Pro answering: search the LLM-chunked store (vector_pro_db), optionally with an
LLM-rewritten query and LLM reranking. Switch those on in rag_pro/config.py.

Same shape as rag.answer: answer_question(question, history) -> (answer, chunks),
so eval.py can grade it.
"""
from datetime import date
import gradio as gr
from chromadb import PersistentClient
from litellm import completion
from pydantic import BaseModel, Field
from tenacity import retry, wait_exponential, stop_after_attempt

from rag_pro import config
from rag_pro.ingest import openrouter, Result
from rag import usage

wait = wait_exponential(multiplier=1, min=2, max=30)

# Same prompt as RAG v1, so a change in scores comes from retrieval, not the prompt
SYSTEM_PROMPT = """
Today's date is {today}.
Your a AI assistant for Sri lankan MSME (medium small medium enterprice )
Your task is to only answer using the provided document text and if the documents dont cover the question , say i dont know , please check with the bank and never guess (never state a specific banks interest rate)
Always provide a disclaimer : not a financial  advice
Every factual claim you take must include a citation to the source document and page number , e.g (treasury_msme_faq.pdf, page 3)
The context below is labeled with its source document and page number - use those exact labels when citing.
If a scheme has an end date or deadline, compare it with today's date. If it has already
passed, say the scheme appears to have ended on that date, and tell the user to confirm with
the Department of Development Finance or their bank. Never say an expired scheme is open.

{context}
"""

REWRITE_PROMPT = """
You are helping a chatbot that answers questions about Sri Lankan government loan schemes for
micro, small and medium enterprises (MSMEs), such as SMELoC, SMELOC2 and the Re-energizing MSME
loan scheme (Component I and Component II). It is about to search its documents for the user's question.

Conversation so far:
{history}

User's current question:
{question}

Rewrite the current question as one short, specific search query that is most likely to find the
relevant passages. Use the conversation to resolve words like "it" or "that scheme" into the actual
scheme name. Keep scheme names, amounts and terms exactly as the user wrote them.

Respond ONLY with the search query, nothing else.
"""

RERANK_PROMPT = """
You are a document re-ranker for a chatbot about Sri Lankan government MSME loan schemes.
You are given a user's question and numbered chunks of text retrieved from the documents.
Order the chunks by how useful they are for answering the question, most useful first.
A chunk about a different scheme than the one asked about is less useful, even if the topic matches.
Include every chunk id you were given, exactly once.
"""


class RankOrder(BaseModel):
    order: list[int] = Field(
        description="All chunk ids, ordered from most relevant to least relevant to the question"
    )


chroma = PersistentClient(path=config.DB_NAME)


def search(query: str, k: int) -> list[tuple[float, Result]]:
    """Embed the query and return the k closest chunks as (distance, chunk), closest first."""
    vector = openrouter.embeddings.create(model=config.EMBEDDING_MODEL, input=[query]).data[0].embedding
    # Looked up on every call, so a re-ingest (which recreates the collection) doesn't
    # leave this process holding a deleted collection
    collection = chroma.get_collection(config.COLLECTION_NAME)
    results = collection.query(query_embeddings=[vector], n_results=k)
    return [
        (distance, Result(page_content=text, metadata=meta))
        for text, meta, distance in zip(results["documents"][0], results["metadatas"][0], results["distances"][0])
    ]


def merge(results: list[tuple[float, Result]]) -> list[Result]:
    """Drop duplicate chunks (found by both queries) and sort by distance, closest first.
    Both queries use the same embedding model, so their distances can be compared."""
    best: dict[str, tuple[float, Result]] = {}
    for distance, chunk in results:
        if chunk.page_content not in best or distance < best[chunk.page_content][0]:
            best[chunk.page_content] = (distance, chunk)
    return [chunk for _, chunk in sorted(best.values(), key=lambda pair: pair[0])]


@retry(wait=wait, stop=stop_after_attempt(3), reraise=True)
def rewrite_query(question: str, history: list[dict]) -> str:
    past = "\n".join(f"{turn['role']}: {turn['content']}" for turn in history) or "(none)"
    prompt = REWRITE_PROMPT.format(history=past, question=question)
    response = completion(model=config.HELPER_MODEL, messages=[{"role": "user", "content": prompt}], temperature=0)
    usage.record(response.usage.prompt_tokens, response.usage.completion_tokens)
    return response.choices[0].message.content.strip()


@retry(wait=wait, stop=stop_after_attempt(3), reraise=True)
def rerank(question: str, chunks: list[Result]) -> list[Result]:
    user_prompt = f"Question: {question}\n\nChunks:\n\n"
    for chunk_id, chunk in enumerate(chunks, start=1):
        user_prompt += f"# CHUNK ID: {chunk_id}\n{chunk.page_content}\n\n"
    messages = [{"role": "system", "content": RERANK_PROMPT}, {"role": "user", "content": user_prompt}]
    response = completion(model=config.HELPER_MODEL, messages=messages, response_format=RankOrder, temperature=0)
    usage.record(response.usage.prompt_tokens, response.usage.completion_tokens)
    order = RankOrder.model_validate_json(response.choices[0].message.content).order

    # The LLM may skip, repeat or invent ids: keep valid ones once, then add any it left out
    ranked_ids = list(dict.fromkeys(i for i in order if 1 <= i <= len(chunks)))
    ranked_ids += [i for i in range(1, len(chunks) + 1) if i not in ranked_ids]
    return [chunks[i - 1] for i in ranked_ids]


def fetch_context(question: str, history: list[dict] | None = None) -> list[Result]:
    """Search -> (rewrite + search again, merge) -> (rerank) -> top FINAL_K."""
    history = history or []
    # Fetching more than FINAL_K only helps when a reranker picks from the extras
    k = config.RETRIEVAL_K if config.USE_RERANK else config.FINAL_K
    results = search(question, k)
    if config.USE_QUERY_REWRITE:
        results += search(rewrite_query(question, history), k)
    chunks = merge(results)
    if config.USE_RERANK:
        # Rank against what the user asked, not the rewritten query
        chunks = rerank(question, chunks)
    return chunks[:config.FINAL_K]


def build_context(chunks: list[Result]) -> str:
    context = ""
    for chunk in chunks:
        # Pages are stored 0-indexed; cite them 1-indexed like the PDF viewer
        context += f"[Source: {chunk.metadata['source']}, Page: {chunk.metadata['page'] + 1}]\n"
        context += f"{chunk.page_content}\n\n"
    return context


def make_messages(question: str, history: list[dict], chunks: list[Result]) -> list[dict]:
    today = date.today().strftime("%d %B %Y")
    system_prompt = SYSTEM_PROMPT.format(context=build_context(chunks), today=today)
    return [{"role": "system", "content": system_prompt}] + history + [{"role": "user", "content": question}]


def answer_question(question: str, history: list[dict]) -> tuple[str, list[Result]]:
    # Gradio history items can carry extra keys; the API only wants role and content
    history = [{"role": turn["role"], "content": turn["content"]} for turn in history
               if turn["role"] in ("user", "assistant")]
    chunks = fetch_context(question, history)
    response = completion(model=config.ANSWER_MODEL, messages=make_messages(question, history, chunks), temperature=0)
    usage.record(response.usage.prompt_tokens, response.usage.completion_tokens)
    return response.choices[0].message.content, chunks


def chat(question: str, history):
    answer, _chunks = answer_question(question, history)
    return answer


if __name__ == "__main__":
    gr.ChatInterface(chat).launch()
