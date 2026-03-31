resource "aws_dynamodb_table" "housing_events" {
  name = local.table_name
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
    Name = local.table_name
    Project = local.project_name
    Stage = local.stage
  }
}

resource "aws_dynamodb_table" "datasets" {
  name = local.datasets_table_name
  billing_mode = "PAY_PER_REQUEST"

  hash_key = "datasetId"

  attribute {
    name = "datasetId"
    type = "S"
  }

  tags = {
    Name = local.datasets_table_name
    Project = local.project_name
    Stage = local.stage
  }
}