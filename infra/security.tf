# ALB security group: allow HTTP (80) from the internet
resource "aws_security_group" "alb" {
  name        = "rag-qa-alb-sg"
  description = "Allow HTTP inbound to the ALB"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description = "HTTP from anywhere"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"          # -1 = all protocols
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# Task security group: allow app port (8000) ONLY from the ALB
resource "aws_security_group" "task" {
  name        = "rag-qa-task-sg"
  description = "Allow app port from the ALB only"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description     = "App port from the ALB"
    from_port       = 8000
    to_port         = 8000
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]   # ← only the ALB, not the whole internet
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
