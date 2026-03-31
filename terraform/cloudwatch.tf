locals {
  lambda_functions = {
    collection = "${local.project_name}-collection-${local.stage}"
    retrieval  = "${local.project_name}-retrieval-${local.stage}"
    analytics  = "${local.project_name}-analytics-${local.stage}"
  }
}

resource "aws_cloudwatch_log_metric_filter" "error_count" {
  for_each = local.lambda_functions

  name           = "cloudbelly-${each.key}-error-count"
  log_group_name = "/aws/lambda/${each.value}"
  pattern        = "{ $.event = \"dynamodb_error\" }"

  metric_transformation {
    name          = "ErrorCount"
    namespace     = "CloudBelly/${each.key}"
    value         = "1"
    default_value = "0"
  }
}

resource "aws_cloudwatch_log_metric_filter" "validation_error_count" {
  name           = "cloudbelly-retrieval-validation-errors"
  log_group_name = "/aws/lambda/${local.lambda_functions.retrieval}"
  pattern        = "{ $.event = \"validation_error\" }"

  metric_transformation {
    name          = "ValidationErrorCount"
    namespace     = "CloudBelly/retrieval"
    value         = "1"
    default_value = "0"
  }
}

resource "aws_cloudwatch_log_metric_filter" "full_scan_count" {
  name           = "cloudbelly-retrieval-full-scans"
  log_group_name = "/aws/lambda/${local.lambda_functions.retrieval}"
  pattern        = "{ $.event = \"full_scan\" }"

  metric_transformation {
    name          = "FullScanCount"
    namespace     = "CloudBelly/retrieval"
    value         = "1"
    default_value = "0"
  }
}

resource "aws_cloudwatch_metric_alarm" "lambda_errors" {
  for_each = local.lambda_functions

  alarm_name          = "cloudbelly-${each.key}-lambda-errors"
  alarm_description   = "Triggers when ${each.key} Lambda has execution errors"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 1
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = 60
  statistic           = "Sum"
  threshold           = 1
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = each.value
  }
}

resource "aws_cloudwatch_metric_alarm" "retrieval_duration" {
  alarm_name          = "cloudbelly-retrieval-high-duration"
  alarm_description   = "Retrieval Lambda p90 duration exceeding 5 seconds"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 2
  metric_name         = "Duration"
  namespace           = "AWS/Lambda"
  period              = 300
  extended_statistic  = "p90"
  threshold           = 5000
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = local.lambda_functions.retrieval
  }
}

resource "aws_cloudwatch_metric_alarm" "dynamodb_errors" {
  for_each = local.lambda_functions

  alarm_name          = "cloudbelly-${each.key}-dynamodb-errors"
  alarm_description   = "DynamoDB errors detected in ${each.key} Lambda logs"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 1
  metric_name         = "ErrorCount"
  namespace           = "CloudBelly/${each.key}"
  period              = 60
  statistic           = "Sum"
  threshold           = 1
  treat_missing_data  = "notBreaching"
}

resource "aws_cloudwatch_metric_alarm" "full_scan_alarm" {
  alarm_name          = "cloudbelly-retrieval-full-scan-frequency"
  alarm_description   = "Full DynamoDB scans occurring frequently"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 1
  metric_name         = "FullScanCount"
  namespace           = "CloudBelly/retrieval"
  period              = 300
  statistic           = "Sum"
  threshold           = 5
  treat_missing_data  = "notBreaching"
}

resource "aws_cloudwatch_dashboard" "cloudbelly" {
  dashboard_name = "CloudBelly-Dev"

  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "metric"
        x      = 0
        y      = 0
        width  = 8
        height = 6
        properties = {
          title   = "Lambda Invocations"
          region  = var.aws_region
          view    = "timeSeries"
          stacked = false
          metrics = [
            ["AWS/Lambda", "Invocations", "FunctionName", local.lambda_functions.collection, { label = "Collection" }],
            ["AWS/Lambda", "Invocations", "FunctionName", local.lambda_functions.retrieval, { label = "Retrieval" }],
            ["AWS/Lambda", "Invocations", "FunctionName", local.lambda_functions.analytics, { label = "Analytics" }]
          ]
          period = 300
          stat   = "Sum"
        }
      },
      {
        type   = "metric"
        x      = 8
        y      = 0
        width  = 8
        height = 6
        properties = {
          title  = "Lambda Errors"
          region = var.aws_region
          view   = "timeSeries"
          metrics = [
            ["AWS/Lambda", "Errors", "FunctionName", local.lambda_functions.collection, { label = "Collection", color = "#d62728" }],
            ["AWS/Lambda", "Errors", "FunctionName", local.lambda_functions.retrieval, { label = "Retrieval", color = "#ff7f0e" }],
            ["AWS/Lambda", "Errors", "FunctionName", local.lambda_functions.analytics, { label = "Analytics", color = "#e377c2" }]
          ]
          period = 300
          stat   = "Sum"
        }
      },
      {
        type   = "metric"
        x      = 16
        y      = 0
        width  = 8
        height = 6
        properties = {
          title  = "Lambda Duration (p90, ms)"
          region = var.aws_region
          view   = "timeSeries"
          metrics = [
            ["AWS/Lambda", "Duration", "FunctionName", local.lambda_functions.collection, { label = "Collection", stat = "p90" }],
            ["AWS/Lambda", "Duration", "FunctionName", local.lambda_functions.retrieval, { label = "Retrieval", stat = "p90" }],
            ["AWS/Lambda", "Duration", "FunctionName", local.lambda_functions.analytics, { label = "Analytics", stat = "p90" }]
          ]
          period = 300
          stat   = "p90"
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 6
        width  = 8
        height = 6
        properties = {
          title  = "Lambda Throttles"
          region = var.aws_region
          view   = "timeSeries"
          metrics = [
            ["AWS/Lambda", "Throttles", "FunctionName", local.lambda_functions.collection, { label = "Collection" }],
            ["AWS/Lambda", "Throttles", "FunctionName", local.lambda_functions.retrieval, { label = "Retrieval" }],
            ["AWS/Lambda", "Throttles", "FunctionName", local.lambda_functions.analytics, { label = "Analytics" }]
          ]
          period = 300
          stat   = "Sum"
        }
      },
      {
        type   = "metric"
        x      = 8
        y      = 6
        width  = 8
        height = 6
        properties = {
          title  = "DynamoDB Errors (from logs)"
          region = var.aws_region
          view   = "timeSeries"
          metrics = [
            ["CloudBelly/collection", "ErrorCount", { label = "Collection DB Errors", color = "#d62728" }],
            ["CloudBelly/retrieval", "ErrorCount", { label = "Retrieval DB Errors", color = "#ff7f0e" }],
            ["CloudBelly/analytics", "ErrorCount", { label = "Analytics DB Errors", color = "#e377c2" }]
          ]
          period = 300
          stat   = "Sum"
        }
      },
      {
        type   = "metric"
        x      = 16
        y      = 6
        width  = 8
        height = 6
        properties = {
          title  = "Full Table Scans (no state param)"
          region = var.aws_region
          view   = "timeSeries"
          metrics = [
            ["CloudBelly/retrieval", "FullScanCount", { label = "Full Scans", color = "#ff7f0e" }]
          ]
          period = 300
          stat   = "Sum"
        }
      },
      {
        type   = "log"
        x      = 0
        y      = 12
        width  = 24
        height = 6
        properties = {
          title  = "Recent Errors and Warnings (all Lambdas)"
          region = var.aws_region
          view   = "table"
          query  = "SOURCE '/aws/lambda/housing-api-retrieval-dev' | SOURCE '/aws/lambda/housing-api-analytics-dev' | SOURCE '/aws/lambda/housing-api-collection-dev' | fields @timestamp, @message | filter @message like /ERROR|WARNING/ | sort @timestamp desc | limit 50"
        }
      }
    ]
  })
}
