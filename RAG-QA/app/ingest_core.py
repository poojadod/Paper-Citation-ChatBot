"""Ingest one PDF into Qdrant: load pages -> split into chunks -> embed -> store."""
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.store import get_vectorstore

# Splits long text into ~500-char chunks with 50-char overlap so context isn't
# cut mid-sentence. Tries to split on paragraphs, then lines, then sentences.
_splitter = RecursiveCharacterTextSplitter(
    chunk_size=500, chunk_overlap=50, separators=["\n\n", "\n", ".", " "]
)


def ingest_pdf(path, filename):
    # Turn the filename into a readable title (e.g. "Attention Is All You Need")
    title = filename.replace(".pdf", "").replace("_", " ").strip()

    # 1. Load the PDF — PyPDFLoader gives one Document PER PAGE
    docs = PyPDFLoader(path).load()
    for d in docs:
        # attach metadata so answers can cite the source later
        d.metadata["paper_title"] = title
        d.metadata["filename"] = filename

    # 2. Split those pages into smaller chunks (better retrieval granularity)
    chunks = _splitter.split_documents(docs)
    for c in chunks:
        c.metadata["paper_title"] = title       # re-attach metadata to every chunk
        c.metadata["filename"] = filename

    # 3. Embed each chunk and store it in Qdrant (add_documents does both)
    get_vectorstore().add_documents(chunks)

    # Return a small summary for the API response
    return {"filename": filename, "title": title, "chunks": len(chunks)}
