import os
import tempfile

from fastapi import FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel

from app.rag import answer_question
from app.ingest_core import ingest_pdf
from app.store import get_client, COLLECTION


from contextlib import asynccontextmanager
from app.sqs_consumer import start_consumer



@asynccontextmanager
async def lifespan(app):
    start_consumer()      # launch the SQS consumer on startup
    yield

app = FastAPI(lifespan=lifespan)     # ← replace your existing app = FastAPI()



class QueryRequest(BaseModel):
    question: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/query")
def query(req: QueryRequest):
    return answer_question(req.question)


@app.post("/ingest")
async def ingest(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="only .pdf files are supported")
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name
    try:
        return ingest_pdf(tmp_path, file.filename)
    finally:
        os.unlink(tmp_path)


@app.get("/papers")
def papers():
    client, titles, offset = get_client(), set(), None
    while True:
        # 1. fetch a batch of stored points (up to 256 at a time)
        points, offset = client.scroll(
            collection_name=COLLECTION, with_payload=True, limit=256, offset=offset
        )
        # 2. pull the paper_title from each point's metadata, add to a SET
        for p in points:
            titles.add((p.payload or {}).get("metadata", {}).get("paper_title", "Unknown"))
        # 3. when there are no more batches, stop
        if offset is None:
            break
    return {"papers": sorted(titles)}   # 4. return the unique titles, alphabetized
