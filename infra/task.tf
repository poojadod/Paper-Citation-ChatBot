resource "aws_cloudwatch_log_group" "app" {
  name              = "/ecs/rag-qa"
  retention_in_days = 7
}

resource "aws_ecs_task_definition" "app" {
  family                   = "rag-qa"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = "1024"
  memory                   = "2048"
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn      = aws_iam_role.ecs_task.arn      # ← NEW

  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = "X86_64"
  }

  container_definitions = jsonencode([
    {
      name         = "rag-qa"
      image        = var.ecr_image
      essential    = true
      portMappings = [{ containerPort = 8000, protocol = "tcp" }]
      environment = [
        { name = "GROQ_API_KEY",   value = var.groq_api_key },
        { name = "QDRANT_URL",     value = var.qdrant_url },
        { name = "QDRANT_API_KEY", value = var.qdrant_api_key },
        { name = "SQS_QUEUE_URL",  value = aws_sqs_queue.ingest.id },   # ← NEW (the consumer reads this)
        { name = "AWS_REGION",     value = var.aws_region } 
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.app.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "ecs"
        }
      }
    }
  ])
}
