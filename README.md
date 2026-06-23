# RAG Research Paper Q&A

A simple Retrieval-Augmented Generation (RAG) chatbot that answers questions about research papers. Drop PDFs into a folder, ingest them into a local vector store, and chat with a bot that cites the paper and page it pulled each answer from.

## How it works

- **`ingest.py`** — loads PDFs from `papers/`, splits them into chunks, embeds them with `sentence-transformers/all-MiniLM-L6-v2`, and stores them in a local ChromaDB.
- **`query.py`** — loads the vector store, retrieves the most relevant chunks for your question, and uses Groq's `llama-3.1-8b-instant` to generate a cited answer. Keeps short-term conversation memory.

## Setup

```bash
cd RAG-QA
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Set your Groq API key (get one at https://console.groq.com):

```bash
export GROQ_API_KEY=your_key_here
```

## Usage

1. Add research paper PDFs to `RAG-QA/papers/`.
2. Ingest them into the vector store:

   ```bash
   python ingest.py
   ```

3. Start the chatbot:

   ```bash
   python query.py
   ```

### Chat commands

| Command  | Action                          |
|----------|---------------------------------|
| `papers` | List the loaded papers          |
| `clear`  | Clear conversation memory       |
| `exit`   | Quit                            |

## Stack

LangChain · ChromaDB · HuggingFace embeddings · Groq (Llama 3.1)
