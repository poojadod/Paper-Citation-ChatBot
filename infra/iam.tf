# Policy that lets ECS tasks assume this role
data "aws_iam_policy_document" "ecs_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}

# The execution role itself
resource "aws_iam_role" "ecs_execution" {
  name               = "rag-qa-ecs-execution-role"
  assume_role_policy = data.aws_iam_policy_document.ecs_assume.json
}

# Attach AWS's managed policy (grants ECR pull + CloudWatch logs)
resource "aws_iam_role_policy_attachment" "ecs_execution" {
  role       = aws_iam_role.ecs_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# Task role — permissions for your APP CODE (S3 read + SQS consume)
resource "aws_iam_role" "ecs_task" {
  name               = "rag-qa-ecs-task-role"
  assume_role_policy = data.aws_iam_policy_document.ecs_assume.json   # reuse existing assume policy
}

data "aws_iam_policy_document" "task_permissions" {
  statement {
    actions   = ["s3:GetObject"]
    resources = ["${aws_s3_bucket.papers.arn}/*"]      # read objects in the bucket
  }
  statement {
    actions   = ["sqs:ReceiveMessage", "sqs:DeleteMessage", "sqs:GetQueueAttributes"]
    resources = [aws_sqs_queue.ingest.arn]              # consume from the queue
  }
}

resource "aws_iam_role_policy" "task_permissions" {
  name   = "rag-qa-task-permissions"
  role   = aws_iam_role.ecs_task.id
  policy = data.aws_iam_policy_document.task_permissions.json
}
