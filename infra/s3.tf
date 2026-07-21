resource "aws_s3_bucket" "papers" {
  bucket        = "rag-qa-papers-386089921957"   # S3 names are GLOBALLY unique → add account id
  force_destroy = true                            # lets `terraform destroy` remove it even if not empty
}
