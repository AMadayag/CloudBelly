output "api_url" {
  description = "API Gateway url"
  value       = aws_apigatewayv2_stage.housing_api.invoke_url
}

output "table_name" {
  description = "DynamoDB table name"
  value       = aws_dynamodb_table.housing_events.name
}

output "bucket_name" {
  description = "S3 bucket name"
  value       = aws_s3_bucket.s3_bucket.bucket
}

output "collection_lambda" {
  value = aws_lambda_function.collection.function_name
}

output "retrieval_lambda" {
  value = aws_lambda_function.retrieval.function_name
}

output "analytics_lambda" {
  value = aws_lambda_function.analytics.function_name
}