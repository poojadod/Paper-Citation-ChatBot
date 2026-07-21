# Dead-letter queue: messages that fail repeatedly land here (no data lost)
resource "aws_sqs_queue" "ingest_dlq" {
  name = "rag-qa-ingest-dlq"
}

# Main queue
resource "aws_sqs_queue" "ingest" {
  name                       = "rag-qa-ingest"
  message_retention_seconds  = 1209600   # 14 days (max buffer while compute is down)
  visibility_timeout_seconds = 300       # 5 min to process before the msg reappears
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.ingest_dlq.arn
    maxReceiveCount     = 5              # try 5x, then send to DLQ
  })
}

# Let S3 send messages to the queue
resource "aws_sqs_queue_policy" "ingest" {
  queue_url = aws_sqs_queue.ingest.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "s3.amazonaws.com" }
      Action    = "sqs:SendMessage"
      Resource  = aws_sqs_queue.ingest.arn
      Condition = { ArnEquals = { "aws:SourceArn" = aws_s3_bucket.papers.arn } }
    }]
  })
}

# S3 → SQS notification on PDF uploads
resource "aws_s3_bucket_notification" "papers" {
  bucket = aws_s3_bucket.papers.id
  queue {
    queue_arn     = aws_sqs_queue.ingest.arn
    events        = ["s3:ObjectCreated:*"]
    filter_suffix = ".pdf"                # only .pdf uploads trigger it
  }
  depends_on = [aws_sqs_queue_policy.ingest]   # policy must exist before S3 can send
}
