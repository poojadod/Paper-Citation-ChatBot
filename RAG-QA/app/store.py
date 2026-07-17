"""Shared, load-once objects used by BOTH querying and ingestion:
the embedding model and the Qdrant vector store. We build them once and reuse."""
import os

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

# ── Config from environment (same code, different values per environment) ──
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")  # compose sets this to http://qdrant:6333
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", "")              # empty locally; a real key in the cloud
COLLECTION = "research_papers"                                # the "table" name inside Qdrant
EMBED_DIM = 384                                               # all-MiniLM-L6-v2 outputs 384-number vectors

# Module-level caches so we don't rebuild these heavy objects on every request.
_embeddings = None
_client = None
_vectorstore = None

def get_embeddings():
    """The local HuggingFace model that turns text -> vectors. Loaded once."""
    global _embeddings
    if _embeddings is None:                       # only build the first time
        _embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            encode_kwargs={"normalize_embeddings": True},  # normalize -> cosine similarity works well
        )
    return _embeddings

def get_client():
    """Raw Qdrant connection. Used for admin tasks (create collection, scroll)."""
    global _client
    if _client is None:
        # api_key=None locally (no auth); a real key when pointing at Qdrant Cloud
        _client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY or None)
    return _client

def get_vectorstore():
    """The LangChain wrapper around Qdrant — what the retriever and ingest use."""
    global _vectorstore
    if _vectorstore is None:
        client = get_client()
        # First run: the collection doesn't exist yet, so create it.
        if not client.collection_exists(COLLECTION):
            client.create_collection(
                collection_name=COLLECTION,
                # tell Qdrant the vector size (384) and how to measure similarity (cosine)
                vectors_config=VectorParams(size=EMBED_DIM, distance=Distance.COSINE),
            )
        _vectorstore = QdrantVectorStore(
            client=client,
            collection_name=COLLECTION,
            embedding=get_embeddings(),           # so it knows how to embed text
        )
    return _vectorstore
