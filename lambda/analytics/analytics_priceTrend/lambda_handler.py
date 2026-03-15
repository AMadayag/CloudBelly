import json
import boto3

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('cloudbelly-dev-housing-events')

def lambda_handler(event, context):
  try {
    datasetId = event["datasetId"]

    response = table.get_item(Key={'datasetId': datasetId})
    item = response.get('Item', {})
  } except ClientError as e:
    raise ClientError(f"[FAIL] DynamoDB get_item failed - {e}")

  return {
    'statusCode': 200,
    'headers': {'Content-Type': 'application/json'},
    'body': json.dumps(item)
  }
