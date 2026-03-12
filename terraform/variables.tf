variable "aws_region" {
  description = "AWS region"
  type = string
  default = "us-east-1"
}

variable "project_name" {
  description = "This is the project name used for naming resource"
  type = string
  default = "housing-api"
}

variable "stage" {
  description = "Deployment stage"
  type = string
  default = "dev"
}

variable "table_name" {
  description = "DynamoDB table name"
  type        = string
  default     = "cloudbelly-dev-housing-events"
}

variable "bucket_name" {
  description = "S3 bucket name for raw housing data"
  type        = string
  default     = "housing-api-raw-data"
}
