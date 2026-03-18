resource "aws_dynamodb_table" "housing_events" {
  name = var.table_name
  billing_mode = "PAY_PER_REQUEST"

  hash_key = "location"
  range_key = "eventKey"

  attribute {
    name = "location"
    type = "S"
  }

  attribute {
    name = "eventKey"
    type = "S"
  }

  tags = {
    Name = var.table_name
    Project = var.project_name
    Stage = var.stage
  }
}