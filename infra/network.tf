# Read the default VPC (we don't create one — reuse what exists)
data "aws_vpc" "default" {
  default = true
}

# Read all subnets in that VPC (the ALB + tasks go here)
data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}


