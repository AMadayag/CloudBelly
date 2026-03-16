import json
import boto3
from botocore.exceptions import ClientError

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table = dynamodb.Table('cloudbelly-dev-housing-events')

def lambda_handler(event, context):
  try:
    # this is for if we use the location and date pars idk
    # params = event["queryStringParameters"] or {}
    # location = params["location"]
    # date = params["date"]
    # response = table.get_item(Key={'location': location, 'date': date})
    # item = response.get('Item', {})
    # this really should be temporary because its lame as hell to query for the ds
    datasetId = event["pathParameters"]["datasetId"]
    response = table.scan(
        FilterExpression=Attr('eventId').eq(datasetId)
    )
    items = response.get('Items', [])
    item = items[0] if items else {}
  except ClientError as e:
    raise RuntimeError(f"[FAIL] DynamoDB get_item failed - {e}")

  return {
    'statusCode': 200,
    'headers': {'Content-Type': 'application/json'},
    'body': json.dumps(item, default=str)
  }
