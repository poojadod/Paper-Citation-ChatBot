variable "aws_region" {
  description = "AWS region to deploy into"
  type        = string
  default     = "us-east-1"
}

variable "ecr_image" {
  description = "The ECR image URI to run"
  type        = string
  default     = "386089921957.dkr.ecr.us-east-1.amazonaws.com/rag-qa:latest"
}

variable "groq_api_key" {
  type      = string
  sensitive = true
}

variable "qdrant_url" {
  type = string
}

variable "qdrant_api_key" {
  type      = string
  sensitive = true
}

