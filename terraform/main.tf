terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

locals {
  stage        = terraform.workspace == "default" ? "dev" : terraform.workspace
  project_name = var.project_name

  table_name          = "cloudbelly-${local.stage}-housing-events"
  datasets_table_name = "cloudbelly-${local.stage}-datasets"
  bucket_name         = "cloudbelly-team-${local.stage}-raw-events"
  lambda_prefix       = "${local.project_name}-${local.stage}"
}
