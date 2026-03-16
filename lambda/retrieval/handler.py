import json
import boto3
from botocore.exceptions import ClientError

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table = dynamodb.Table('cloudbelly-dev-housing-events')

def lambda_handler(event, context):
  route = event.get("routeKey", "")
  
  if route == "GET /api/v1/datasets/{datasetId}":
    return get_dataset_by_id(event)
  else:
    return {'statusCode': 404, 'body': json.dumps('Not found')}


def get_dataset_by_id(event):
  try:
    datasetId = event["pathParameters"]["datasetId"]
    response = table.scan(
        FilterExpression=Attr('eventId').eq(datasetId)
    )
    items = response.get('Items', [])
    item = items[0] if items else {}
  except ClientError as e:
    raise RuntimeError(f"[FAIL] DynamoDB scan failed - {e}")

  return {
    'statusCode': 200,
    'headers': {'Content-Type': 'application/json'},
    'body': json.dumps(item, default=str)
  }
