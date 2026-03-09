resource "aws_dynamodb_table" "housing_events" {
  name = var.table_name
  billing_mode = "PAY_PER_REQUEST"

  hash_key = "suburb"
  range_key = "period"

  attribute {
    name = "suburb"
    type = "S"
  }

  attribute {
    name = "period"
    type = "S"
  }

  tags = {
    Name = var.table_name
    Project = var.project_name
    Stage = var.stage
  }
}