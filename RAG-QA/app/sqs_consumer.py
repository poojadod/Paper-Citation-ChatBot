"""Background worker: long-poll SQS for S3 upload events and ingest each new PDF."""
import json
import os
import tempfile
import threading
import time
from urllib.parse import unquote_plus

import boto3

from app.ingest_core import ingest_pdf

SQS_QUEUE_URL = os.getenv("SQS_QUEUE_URL", "")
AWS_REGION    = os.getenv("AWS_REGION", "us-east-1")


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
                    print(f"[sqs] error processing message: {e}")
        except Exception as e:
            print(f"[sqs] receive error: {e}")
            time.sleep(5)


def start_consumer():
    if not SQS_QUEUE_URL:
        print("[sqs] SQS_QUEUE_URL not set — consumer disabled")
        return
    threading.Thread(target=_poll_loop, daemon=True).start()
