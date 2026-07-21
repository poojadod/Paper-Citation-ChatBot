# The Application Load Balancer — public front door
resource "aws_lb" "main" {
  name               = "rag-qa-alb"
  internal           = false                        # false = internet-facing (public)
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]  # the ALB SG (port 80 open)
  subnets            = data.aws_subnets.default.ids  # spread across the default subnets
}

# Target group — where the ALB forwards traffic (your tasks), with the health check
resource "aws_lb_target_group" "main" {
  name        = "rag-qa-tg"
  port        = 8000            # the container port
  protocol    = "HTTP"
  vpc_id      = data.aws_vpc.default.id
  target_type = "ip"           # ← REQUIRED for Fargate (tasks get their own IPs)

  health_check {
    path                = "/health"   # ← the health check path (what tripped you up manually!)
    protocol            = "HTTP"
    matcher             = "200"       # expect HTTP 200
    interval            = 30
    timeout             = 5
    healthy_threshold   = 2
    unhealthy_threshold = 3
  }
}

# Listener — the ALB listens on port 80 and forwards to the target group
resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.main.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.main.arn
  }
}
