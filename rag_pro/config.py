"""RAG Pro settings in one place. ingest.py and answer.py both read from here, and eval runs
save a copy of these values next to their scores, so every run records which features were on.

After changing CHUNK_MODEL, AVERAGE_CHUNK_SIZE or EMBEDDING_MODEL, rebuild the vector store:
    uv run python -m rag_pro.ingest
The flags and K values below only affect answering, so they need no re-ingest.
"""
from pathlib import Path

DB_NAME = str(Path(__file__).parent.parent / "vector_pro_db")
COLLECTION_NAME = "docs"

# Ingest (ingest.py)
CHUNK_MODEL = "openrouter/openai/gpt-4.1-nano"
AVERAGE_CHUNK_SIZE = 500      # characters; only a hint to the chunking LLM
EMBEDDING_MODEL = "openai/text-embedding-3-large"   # through OpenRouter; same at ingest and query time

# Answering (answer.py)
ANSWER_MODEL = "openrouter/openai/gpt-4.1-nano"
HELPER_MODEL = "openrouter/openai/gpt-4.1-nano"     # query rewriting and reranking

USE_QUERY_REWRITE = False     # also search with an LLM-rewritten query, merge the two result lists
USE_RERANK = False            # LLM sorts the candidates by relevance before cutting to FINAL_K

RETRIEVAL_K = 20              # candidates per search when reranking (the reranker picks from these)
FINAL_K = 10                  # chunks the answer model gets


def as_dict() -> dict:
    """Snapshot of the settings, saved with each eval run."""
    return {
        "chunk_model": CHUNK_MODEL,
        "average_chunk_size": AVERAGE_CHUNK_SIZE,
        "embedding_model": EMBEDDING_MODEL,
        "answer_model": ANSWER_MODEL,
        "helper_model": HELPER_MODEL,
        "query_rewrite": USE_QUERY_REWRITE,
        "rerank": USE_RERANK,
        "retrieval_k": RETRIEVAL_K if USE_RERANK else FINAL_K,
        "final_k": FINAL_K,
    }
