"""Background worker: long-poll SQS for S3 upload events and ingest each new PDF."""
import json
import os
import tempfile
import threading
import time
from urllib.parse import unquote_plus
from qdrant_client.models import FieldCondition, Filter, MatchValue
from app.store import get_client, COLLECTION

import boto3

from app.ingest_core import ingest_pdf

SQS_QUEUE_URL = os.getenv("SQS_QUEUE_URL", "")
AWS_REGION    = os.getenv("AWS_REGION", "us-east-1")

S3_BUCKET = os.getenv("S3_BUCKET", "")

def _already_ingested(filename):
    """True if Qdrant already has chunks for this file (skip re-ingest)."""
    res = get_client().count(
        collection_name=COLLECTION,
        count_filter=Filter(
            must=[FieldCondition(key="metadata.filename", match=MatchValue(value=filename))]
        ),
        exact=True,
    )
    return res.count > 0


def backfill_from_s3():
    """On boot: ingest any PDFs in the bucket that aren't in Qdrant yet (self-healing)."""
    if not S3_BUCKET:
        print("[backfill] S3_BUCKET not set — skipping")
        return
    s3 = boto3.client("s3", region_name=AWS_REGION)
    ingested = skipped = 0
    for page in s3.get_paginator("list_objects_v2").paginate(Bucket=S3_BUCKET):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            if not key.lower().endswith(".pdf"):
                continue
            filename = os.path.basename(key)
            if _already_ingested(filename):          # idempotent: skip what's already there
                skipped += 1
                continue
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                s3.download_fileobj(S3_BUCKET, key, tmp)
                tmp_path = tmp.name
            try:
                ingest_pdf(tmp_path, filename)
                ingested += 1
                print(f"[backfill] ingested {key}")
            except Exception as e:
                print(f"[backfill] error on {key}: {e}")
            finally:
                os.unlink(tmp_path)
    print(f"[backfill] done — ingested {ingested}, skipped {skipped} (already present)")


def start_backfill():
    threading.Thread(target=backfill_from_s3, daemon=True).start()


def _process_event(s3, body):
    for record in body.get("Records", []):
        bucket = record["s3"]["bucket"]["name"]
        key    = unquote_plus(record["s3"]["object"]["key"])
        if not key.lower().endswith(".pdf"):
            continue
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            s3.download_fileobj(bucket, key, tmp)
            tmp_path = tmp.name
        try:
            result = ingest_pdf(tmp_path, os.path.basename(key))
            print(f"[sqs] ingested {key}: {result}")
        finally:
            os.unlink(tmp_path)


def _poll_loop():
    sqs = boto3.client("sqs", region_name=AWS_REGION)
    s3  = boto3.client("s3",  region_name=AWS_REGION)
    print(f"[sqs] consumer started, polling {SQS_QUEUE_URL}")
    while True:
        try:
            resp = sqs.receive_message(QueueUrl=SQS_QUEUE_URL, MaxNumberOfMessages=5, WaitTimeSeconds=20)
            for msg in resp.get("Messages", []):
                try:
                    _process_event(s3, json.loads(msg["Body"]))
                    sqs.delete_message(QueueUrl=SQS_QUEUE_URL, ReceiptHandle=msg["ReceiptHandle"])
                except Exception as e:
                    import traceback
                    print(f"[sqs] error processing message: {repr(e)}")
                    traceback.print_exc()

            print(f"[sqs] receive error: {e}")
            time.sleep(5)


def start_consumer():
    if not SQS_QUEUE_URL:
        print("[sqs] SQS_QUEUE_URL not set — consumer disabled")
        return
    threading.Thread(target=_poll_loop, daemon=True).start()
