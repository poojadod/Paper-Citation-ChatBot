"""Ingest one PDF into Qdrant: load pages -> split -> embed -> upsert.
Idempotent: re-ingesting the same filename replaces its old chunks (no duplicates),
which matters because SQS delivers at-least-once."""
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from qdrant_client.models import FieldCondition, Filter, FilterSelector, MatchValue

from app.store import get_client, get_vectorstore, COLLECTION

_splitter = RecursiveCharacterTextSplitter(
    chunk_size=500, chunk_overlap=50, separators=["\n\n", "\n", ".", " "]
)


def _delete_existing(filename):
    """Remove any prior chunks for this file so re-ingest is idempotent."""
    get_client().delete(
        collection_name=COLLECTION,
        points_selector=FilterSelector(
            filter=Filter(
                must=[FieldCondition(key="metadata.filename", match=MatchValue(value=filename))]
            )
        ),
    )


def ingest_pdf(path, filename):
    title = filename.replace(".pdf", "").replace("_", " ").strip()

    # 1. load the PDF (one Document per page) + tag metadata
    docs = PyPDFLoader(path).load()
    for d in docs:
        d.metadata["paper_title"] = title
        d.metadata["filename"] = filename

    # 2. split into chunks + re-tag
    chunks = _splitter.split_documents(docs)
    for c in chunks:
        c.metadata["paper_title"] = title
        c.metadata["filename"] = filename

    # 3. idempotent write: delete old chunks for this file, then add fresh
    _delete_existing(filename)
    get_vectorstore().add_documents(chunks)

    return {"filename": filename, "title": title, "chunks": len(chunks)}
