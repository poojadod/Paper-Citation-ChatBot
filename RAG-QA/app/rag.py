"""RAG query logic: retrieve relevant chunks from Qdrant, then ask Groq to
answer using those chunks as context."""
import os

from langchain.chains import RetrievalQA
from langchain_core.prompts import PromptTemplate
from langchain_groq import ChatGroq

from app.store import get_vectorstore          # our shared Qdrant vector store

_chain = None                                  # cache the assembled chain (build once)


def _build_chain():
    # 1. retriever = "given a question, fetch the k most relevant chunks from Qdrant"
    retriever = get_vectorstore().as_retriever(
        search_type="similarity",              # find chunks closest in MEANING
        search_kwargs={"k": 5},                # return the top 5
    )

    # 2. the LLM that writes the final answer (Groq's Llama)
    llm = ChatGroq(
        model="llama-3.1-8b-instant",
        temperature=0,                         # 0 = focused/deterministic, not creative
        api_key=os.getenv("GROQ_API_KEY"),     # read the secret from the environment
    )

    # 3. instructions: answer ONLY from the retrieved context (reduces hallucination)
    prompt = PromptTemplate(
        input_variables=["context", "question"],   # placeholders the chain fills in
        template="""You are a research assistant. Use the context below to answer the question.
Be specific and detailed. Use information directly from the context.
Only say information is not available if it truly does not appear anywhere in the context.

Context:
{context}

Question: {question}

Detailed Answer:""",
    )

    # 4. wire it together: retrieve -> stuff chunks into {context} -> LLM -> answer
    return RetrievalQA.from_chain_type(
        llm=llm,
        retriever=retriever,
        return_source_documents=True,          # also return WHICH chunks were used
        chain_type_kwargs={"prompt": prompt},
    )


def get_chain():
    """Build the chain once, reuse it after (loads the model on first call)."""
    global _chain
    if _chain is None:
        _chain = _build_chain()
    return _chain


def answer_question(question):
    # invoke() runs the whole pipeline; RetrievalQA uses "query" as the input key
    result = get_chain().invoke({"query": question})

    # Build a clean, de-duplicated list of sources (paper title + page)
    seen, sources = set(), []
    for doc in result["source_documents"]:
        title = doc.metadata.get("paper_title", "Unknown")
        page = doc.metadata.get("page", "N/A")
        if isinstance(page, int):
            page += 1                           # PDF pages are 0-indexed; show human page number
        key = f"{title}|{page}"
        if key not in seen:                     # skip duplicates
            seen.add(key)
            sources.append({"paper_title": title, "page": page})

    # "result" is the answer text; return it plus the sources as JSON
    return {"answer": result["result"], "sources": sources}
