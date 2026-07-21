output "app_url" {
  description = "Public URL of the app"
  value       = "http://${aws_lb.main.dns_name}"
}

output "bucket_name" {
  value = aws_s3_bucket.papers.bucket
}
