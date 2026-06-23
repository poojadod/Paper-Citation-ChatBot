# ingest.py

import os
import re
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma

PAPERS_FOLDER = "./papers"
CHROMA_DIR    = "./chroma_db"

# ── Helper — extract title from PDF ──────────────────────────────────
def extract_title(filepath, documents):
    filename = os.path.basename(filepath)
    # Just use filename as title — clean and simple
    title = filename.replace(".pdf", "").replace("_", " ").strip()
    return title

# ── Step 1: Load all PDFs ─────────────────────────────────────────────
print("=" * 50)
print("RESEARCH PAPER INGESTION")
print("=" * 50)

pdf_files = [
    f for f in os.listdir(PAPERS_FOLDER)
    if f.endswith(".pdf")
]

if not pdf_files:
    print("No PDFs found in papers/ folder!")
    print("Drop some research paper PDFs in there and re-run.")
    exit()

print(f"\nFound {len(pdf_files)} papers:")
for f in pdf_files:
    print(f"  - {f}")

# ── Step 2: Process each paper ────────────────────────────────────────
all_chunks = []

splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=50,
    separators=["\n\n", "\n", ".", " "]
)

for filename in pdf_files:
    filepath = os.path.join(PAPERS_FOLDER, filename)
    print(f"\nProcessing: {filename}")

    # Load PDF — one Document per page
    loader    = PyPDFLoader(filepath)
    documents = loader.load()
    print(f"  Pages loaded: {len(documents)}")

    # Extract paper title
    title = extract_title(filepath, documents)
    print(f"  Title detected: {title}")

    # Add rich metadata to every page
    for doc in documents:
        doc.metadata["paper_title"] = title
        doc.metadata["filename"]    = filename
        # page is already in metadata as doc.metadata["page"]

    # Split pages into chunks
    chunks = splitter.split_documents(documents)
    print(f"  Chunks created: {len(chunks)}")

    # Verify metadata carried through
    # Every chunk should have paper_title, filename, page
    for chunk in chunks:
        chunk.metadata["paper_title"] = title   # ensure it's on every chunk
        chunk.metadata["filename"]    = filename

    all_chunks.extend(chunks)

print(f"\nTotal chunks across all papers: {len(all_chunks)}")

# ── Step 3: Embed and store ───────────────────────────────────────────
print("\nLoading embedding model...")
embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2",
    encode_kwargs={"normalize_embeddings": True}
)

print("Storing in ChromaDB...")

# Delete existing DB if re-ingesting
if os.path.exists(CHROMA_DIR):
    import shutil
    shutil.rmtree(CHROMA_DIR)
    print("Cleared old ChromaDB")

vectorstore = Chroma.from_documents(
    documents=all_chunks,
    embedding=embeddings,
    persist_directory=CHROMA_DIR,
    collection_name="research_papers"
)

print(f"\nDone! {vectorstore._collection.count()} chunks stored.")

# ── Step 4: Verify ────────────────────────────────────────────────────
print("\nVerification — papers indexed:")
collection = vectorstore._collection
metadatas  = collection.get(include=["metadatas"])["metadatas"]

# Get unique paper titles
titles = list(set(m["paper_title"] for m in metadatas))
for title in titles:
    count = sum(1 for m in metadatas if m["paper_title"] == title)
    print(f"  [{count} chunks] {title}")

print("\nReady to query!")