"""Shared, load-once objects used by BOTH querying and ingestion:
the embedding model, the Qdrant client, and the Qdrant vector store.
Built once and reused — that's why we run a warm container, not Lambda."""
import os

from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams
from qdrant_client.models import Distance, PayloadSchemaType, VectorParams


# ── Config from environment (same code, different values per environment) ──
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")   # local compose vs Qdrant Cloud
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", "")               # empty locally; real key in the cloud
COLLECTION = "research_papers"                                 # the "table" name inside Qdrant
EMBED_DIM = 384                                                # all-MiniLM-L6-v2 outputs 384-dim vectors

# Module-level caches so these heavy objects are built only once.
_embeddings = None
_client = None
_vectorstore = None


def get_embeddings():
    """The local HuggingFace model that turns text -> vectors. Loaded once."""
    global _embeddings
    if _embeddings is None:
        _embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            encode_kwargs={"normalize_embeddings": True},  # normalize -> cosine similarity
        )
    return _embeddings


def get_client():
    """Raw Qdrant connection. Used for creating the collection, counts, scrolls."""
    global _client
    if _client is None:
        _client = QdrantClient(
            url=QDRANT_URL,
            api_key=QDRANT_API_KEY or None,   # None locally (no auth), real key for the cloud
            timeout=60,                       # allow up to 60s for cloud uploads (default ~5s is too short)
        )
    return _client


def get_vectorstore():
    """The LangChain wrapper around Qdrant — what the retriever and ingest use."""
    global _vectorstore
    if _vectorstore is None:
        client = get_client()
        # First run: create the collection if it doesn't exist yet.
        if not client.collection_exists(COLLECTION):
            client.create_collection(
                collection_name=COLLECTION,
                vectors_config=VectorParams(size=EMBED_DIM, distance=Distance.COSINE),
            )
        
        # keyword index on metadata.filename → enables filter/delete by filename (idempotency)
        try:
            client.create_payload_index(
                collection_name=COLLECTION,
                field_name="metadata.filename",
                field_schema=PayloadSchemaType.KEYWORD,
            )
        except Exception:
            pass   # already exists → fine

        _vectorstore = QdrantVectorStore(
            client=client,
            collection_name=COLLECTION,
            embedding=get_embeddings(),
        )
    return _vectorstore
