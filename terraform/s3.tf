resource "aws_s3_bucket" "s3_bucket" {
  bucket = var.bucket_name

  tags = {
    Name    = var.bucket_name
    Project = var.project_name
    Stage   = var.stage
  }
}

#enabled versioning for our bucket
resource "aws_s3_bucket_versioning" "s3_bucket" {
  bucket = aws_s3_bucket.s3_bucket.id

  versioning_configuration {
    status = "Enabled"
  }
}