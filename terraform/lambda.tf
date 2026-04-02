locals {
  lab_role_arn = "arn:aws:iam::449844455297:role/LabRole"
}

resource "aws_lambda_function" "collection" {
  filename = "../lambda/collection/handler.zip"
  function_name = "${local.project_name}-collection-${local.stage}"
  role = local.lab_role_arn
  handler = "handler.lambda_handler"
  runtime = "python3.11"
  timeout = 60

  environment {
    variables = {
      TABLE_NAME  = local.table_name
      DATASETS_TABLE_NAME = local.datasets_table_name
      BUCKET_NAME = local.bucket_name
      STAGE = local.stage
    }
  }

  tags = {
    Project = local.project_name
    Stage = local.stage
  }
}

resource "aws_lambda_function" "retrieval" {
  filename = "../lambda/retrieval/handler.zip"
  function_name = "${local.project_name}-retrieval-${local.stage}"
  role = local.lab_role_arn
  handler = "handler.lambda_handler"
  runtime = "python3.11"
  timeout = 30

  environment {
    variables = {
      TABLE_NAME  = local.table_name
      DATASETS_TABLE_NAME = local.datasets_table_name
      BUCKET_NAME = local.bucket_name
      STAGE = local.stage
    }
  }

  tags = {
    Project = local.project_name
    Stage = local.stage
  }
}

resource "aws_lambda_function" "analytics" {
  filename = "../lambda/analytics/handler.zip"
  function_name = "${local.project_name}-analytics-${local.stage}"
  role = local.lab_role_arn
  handler = "handler.lambda_handler"
  runtime = "python3.11"
  timeout = 30

  environment {
    variables = {
      TABLE_NAME  = local.table_name
      DATASETS_TABLE_NAME = local.datasets_table_name
      BUCKET_NAME = local.bucket_name
      STAGE = local.stage
    }
  }

  tags = {
    Project = local.project_name
    Stage = local.stage
  }
}

resource "aws_lambda_function" "testing" {
  filename      = "../lambda/testing/handler.zip"
  function_name = "${local.project_name}-testing-${local.stage}"
  role          = local.lab_role_arn
  handler       = "handler.lambda_handler"
  runtime       = "python3.11"
  timeout       = 60

  environment {
    variables = {
      API_BASE_URL = "https://tvfiek3hzi.execute-api.us-east-1.amazonaws.com/dev"
      STAGE        = local.stage
    }
  }

  tags = {
    Project = local.project_name
    Stage   = local.stage
  }
}