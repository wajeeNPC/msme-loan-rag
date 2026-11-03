"""RAG settings in one place. ingest.py and answer.py both read from here, so they can't
drift apart, and eval runs save a copy of these values next to their scores.

After changing CHUNK_SIZE, CHUNK_OVERLAP or EMBEDDING_MODEL, rebuild the vector store
(vectors from one embedding model can't be searched with another):
    uv run python -m rag.ingest
"""

DB_NAME = "vector_db"

# Chunking (ingest.py)
CHUNK_SIZE = 1500
CHUNK_OVERLAP = 300

# Embeddings: must be the same model at ingest time and at question time.
# Pick one from the list below. Names starting with "openrouter:" go through the
# OpenRouter API (paid, uses OPENROUTER_API_KEY); the rest run locally for free.
EMBEDDING_MODEL = "openrouter:openai/text-embedding-3-large"

# --- Local (HuggingFace, free, downloaded on first use) ---
#   "all-MiniLM-L6-v2"                          RAG v1. Small and fast, reads ~256 tokens per chunk
#   "BAAI/bge-small-en-v1.5"                    Stronger than MiniLM, reads 512 tokens
#   "BAAI/bge-base-en-v1.5"                     Bigger bge: better, slower
# --- OpenRouter (paid per token; price per 1M tokens, checked Nov 2026) ---
#   "openrouter:openai/text-embedding-3-small"  $0.02  - popular default, 8k tokens
#   "openrouter:openai/text-embedding-3-large"  $0.13  - stronger OpenAI model
#   "openrouter:baai/bge-m3"                    $0.01  - multilingual (Sinhala/Tamil later), 8k tokens
#   "openrouter:qwen/qwen3-embedding-8b"        $0.01  - strong, very long input
# Full list: https://openrouter.ai/api/v1/embeddings/models

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# Retrieval + answering (answer.py)
RETRIEVAL_K = 10
ANSWER_MODEL = "openai/gpt-4.1-nano"


def get_embeddings():
    """Build the embedding model named in EMBEDDING_MODEL.
    ingest.py and answer.py both call this, so they always use the same one."""
    if EMBEDDING_MODEL.startswith("openrouter:"):
        import os
        from dotenv import load_dotenv
        from langchain_openai import OpenAIEmbeddings

        load_dotenv(override=True)
        return OpenAIEmbeddings(
            model=EMBEDDING_MODEL.removeprefix("openrouter:"),
            base_url=OPENROUTER_BASE_URL,
            api_key=os.getenv("OPENROUTER_API_KEY"),
            # Send plain text. Otherwise LangChain sends OpenAI token ids,
            # which non-OpenAI endpoints like OpenRouter may not accept.
            check_embedding_ctx_length=False,
        )

    from langchain_huggingface import HuggingFaceEmbeddings
    # Normalized vectors make Chroma's distance behave like cosine similarity,
    # which is what bge models are trained for (MiniLM is already normalized).
    return HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL,
                                 encode_kwargs={"normalize_embeddings": True})


def as_dict() -> dict:
    """Snapshot of the settings, saved with each eval run."""
    return {
        "chunk_size": CHUNK_SIZE,
        "chunk_overlap": CHUNK_OVERLAP,
        "embedding_model": EMBEDDING_MODEL,
        "retrieval_k": RETRIEVAL_K,
        "answer_model": ANSWER_MODEL,
    }
