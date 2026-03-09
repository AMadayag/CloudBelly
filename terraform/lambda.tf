data "aws_iam_role" "lab_role" {
  name = "LabRole"
}

resource "aws_lambda_function" "collection" {
  filename      = "../lambda/collection/handler.zip"
  function_name = "${var.project_name}-collection-${var.stage}"
  role          = data.aws_iam_role.lab_role.arn
  handler       = "handler.lambda_handler"
  runtime       = "python3.11"
  timeout       = 60

  environment {
    variables = {
      TABLE_NAME  = var.table_name
      BUCKET_NAME = var.bucket_name
      STAGE       = var.stage
    }
  }

  tags = {
    Project = var.project_name
    Stage   = var.stage
  }
}

resource "aws_lambda_function" "retrieval" {
  filename      = "../lambda/retrieval/handler.zip"
  function_name = "${var.project_name}-retrieval-${var.stage}"
  role          = data.aws_iam_role.lab_role.arn
  handler       = "handler.lambda_handler"
  runtime       = "python3.11"
  timeout       = 30

  environment {
    variables = {
      TABLE_NAME  = var.table_name
      BUCKET_NAME = var.bucket_name
      STAGE       = var.stage
    }
  }

  tags = {
    Project = var.project_name
    Stage   = var.stage
  }
}

resource "aws_lambda_function" "analytics" {
  filename      = "../lambda/analytics/handler.zip"
  function_name = "${var.project_name}-analytics-${var.stage}"
  role          = data.aws_iam_role.lab_role.arn
  handler       = "handler.lambda_handler"
  runtime       = "python3.11"
  timeout       = 30

  environment {
    variables = {
      TABLE_NAME  = var.table_name
      BUCKET_NAME = var.bucket_name
      STAGE       = var.stage
    }
  }

  tags = {
    Project = var.project_name
    Stage   = var.stage
  }
}