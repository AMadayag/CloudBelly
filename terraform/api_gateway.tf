resource "aws_apigatewayv2_api" "housing_api" {
  name = "${var.project_name}-api-${var.stage}"
  protocol_type = "HTTP"

  cors_configuration {
    allow_origins = [*]
    allow_methods = ["GET", "OPTIONS"]
    allow_headers = ["Content-Type"]
  }
}

resource "aws_apigatewayv2_stage" "housing_api" {
  api_id = aws_apigatewayv2_api.housing_api.id
  name = var.stage
  auto_deploy = true
}

resource "aws_apigatewayv2_integration" "retrieval" {
  api_id = aws_apigatewayv2_api.housing_api.id
  integration_type = "AWS_PROXY"
  integration_uri = aws_lambda_function.retrieval.invoke_arn
  payload_format_version= "2.0"
}?

resource "aws_apigatewayv2_route" "get_events" {
  api_id = aws_apigatewayv2_api.housing_api.id
  route_key = "GET /api/v1/events"
  target = "integrations/${aws_apigatewayv2_integration.retrieval.id}"
}

resource "aws_apigatewayv2_route" "get_datasets" {
  api_id = aws_apigatewayv2_api.housing_api.id
  route_key = "GET /api/v1/datasets"
  target = "integrations/${aws_apigatewayv2_integration.retrieval.id}"
}

resource "aws_apigatewayv2_route" "get_dataset_by_id" {
  api_id = aws_apigatewayv2_api.housing_api.id
  route_key = "GET /api/v1/datasets/{datasetId}"
  target = "integrations/${aws_apigatewayv2_integration.retrieval.id}"
}

resource "aws_apigatewayv2_api" "analytics" {
  api_id = aws_apigatewayv2_api.housing_api.id
  integration_type = "AWS_PROXY"
  integration_uri = aws_lambda_function.analytics.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "price_trend" {
  api_id = aws_apigatewayv2_api.housing_api.id
  route_key = "GET /api/v1/analytics/price-trend"
  target = "integrations/${aws_apigatewayv2_integration.analytics.id}"
}

resource "aws_apigatewayv2_route" "summary" {
  api_id = aws_apigatewayv2_api.housing_api.id
  route_key = "GET /api/v1/analytics/summary"
  target = "integrations/${aws_apigatewayv2_integration.analytics.id}"
}

resource "aws_lambda_permission" "retrieval" {
  statement_id  = "AllowAPIGatewayInvoke"
  action = "lambda:InvokeFunction"
  function_name = aws_lambda_function.retrieval.function_name
  principal = "apigateway.amazonaws.com"
  source_arn = "${aws_apigatewayv2_api.housing_api.execution_arn}/*/*"
}

resource "aws_lambda_permission" "analytics" {
  statement_id  = "AllowAPIGatewayInvoke"
  action = "lambda:InvokeFunction"
  function_name = aws_lambda_function.analytics.function_name
  principal = "apigateway.amazonaws.com"
  source_arn = "${aws_apigatewayv2_api.housing_api.execution_arn}/*/*"
}

