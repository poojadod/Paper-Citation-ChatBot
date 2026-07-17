import warnings
warnings.filterwarnings("ignore")

from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.llms import Ollama
from langchain_groq import ChatGroq
from langchain.memory import ConversationBufferWindowMemory
from langchain.chains import ConversationalRetrievalChain
from langchain_core.prompts import PromptTemplate
import os


CHROMA_DIR = "./chroma_db"

# ── Load components ───────────────────────────────────────────────────
print("Loading components...")

embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2",
    encode_kwargs={"normalize_embeddings": True}
)

vectorstore = Chroma(
    persist_directory=CHROMA_DIR,
    embedding_function=embeddings,
    collection_name="research_papers"
)


llm = ChatGroq(
     model="llama-3.1-8b-instant",
    temperature=0,
    api_key=os.getenv("GROQ_API_KEY")
)

retriever = vectorstore.as_retriever(
    search_type="similarity",
    search_kwargs={"k": 5}
)

# ── Memory ───────────────────
memory = ConversationBufferWindowMemory(
    k=5,
    memory_key="chat_history",
    return_messages=True,    
    output_key="answer"
)

# ── Citation prompt ──────────

qa_prompt = PromptTemplate(
    input_variables=["context", "question"],
    template="""You are a research assistant. Use the context below to answer the question.
Be specific and detailed. Use information directly from the context.
Only say information is not available if it truly does not appear anywhere in the context.

Context:
{context}

Question: {question}

Detailed Answer:"""
)


# ── Build chain ───────────────────────────────────────────────────────
chain = ConversationalRetrievalChain.from_llm(
    llm=llm,
    retriever=retriever,
    memory=memory,
    return_source_documents=True,
    combine_docs_chain_kwargs={"prompt": qa_prompt},
    verbose=False
)

# ── Show loaded papers ────────────────────────────────────────────────
collection = vectorstore._collection
metadatas  = collection.get(include=["metadatas"])["metadatas"]
titles     = list(set(m["paper_title"] for m in metadatas))

print("\n" + "=" * 50)
print("RESEARCH PAPER Q&A BOT")
print("=" * 50)
print("\nPapers loaded:")
for title in titles:
    print(f"  📄 {title}")

print("\nCommands: 'papers' | 'clear' | 'exit'\n")

# ── Chat loop ─────────────────────────────────────────────────────────
while True:
    question = input("You: ").strip()

    if not question:
        continue
    if question.lower() == "exit":
        print("Goodbye!")
        break
    if question.lower() == "clear":
        memory.clear()
        print("Memory cleared!\n")
        continue
    if question.lower() == "papers":
        for title in titles:
            print(f"  📄 {title}")
        print()
        continue

    result  = chain.invoke({"question": question})
    answer  = result["answer"]
    sources = result["source_documents"]

    print(f"\nBot: {answer}")

    print("\nSources:")
    seen = set()
    for doc in sources:
        title = doc.metadata.get("paper_title", "Unknown")
        page  = doc.metadata.get("page", "N/A")
        if isinstance(page, int):
            page = page + 1
        key = f"{title} — Page {page}"
        if key not in seen:
            print(f"  📄 {key}")
            seen.add(key)
    print()