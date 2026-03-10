locals {
  lab_role_arn = "arn:aws:iam::449844455297:role/LabRole"
}

resource "aws_lambda_function" "collection" {
  filename = "../lambda/collection/handler.zip"
  function_name = "${var.project_name}-collection-${var.stage}"
  role = local.lab_role_arn
  handler = "handler.lambda_handler"
  runtime = "python3.11"
  timeout = 60

  environment {
    variables = {
      TABLE_NAME  = var.table_name
      BUCKET_NAME = var.bucket_name
      STAGE = var.stage
    }
  }

  tags = {
    Project = var.project_name
    Stage = var.stage
  }
}

resource "aws_lambda_function" "retrieval" {
  filename = "../lambda/retrieval/handler.zip"
  function_name = "${var.project_name}-retrieval-${var.stage}"
  role = local.lab_role_arn
  handler = "handler.lambda_handler"
  runtime = "python3.11"
  timeout = 30

  environment {
    variables = {
      TABLE_NAME  = var.table_name
      BUCKET_NAME = var.bucket_name
      STAGE = var.stage
    }
  }

  tags = {
    Project = var.project_name
    Stage = var.stage
  }
}

resource "aws_lambda_function" "analytics" {
  filename = "../lambda/analytics/handler.zip"
  function_name = "${var.project_name}-analytics-${var.stage}"
  role = local.lab_role_arn
  handler = "handler.lambda_handler"
  runtime = "python3.11"
  timeout = 30

  environment {
    variables = {
      TABLE_NAME  = var.table_name
      BUCKET_NAME = var.bucket_name
      STAGE = var.stage
    }
  }

  tags = {
    Project = var.project_name
    Stage = var.stage
  }
}