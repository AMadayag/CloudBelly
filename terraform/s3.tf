resource "aws_s3_bucket" "s3_bucket" {
  bucket = local.bucket_name

  tags = {
    Name    = local.bucket_name
    Project = local.project_name
    Stage   = local.stage
  }
}

#enabled versioning for our bucket
resource "aws_s3_bucket_versioning" "s3_bucket" {
  bucket = aws_s3_bucket.s3_bucket.id

  versioning_configuration {
    status = "Enabled"
  }
}