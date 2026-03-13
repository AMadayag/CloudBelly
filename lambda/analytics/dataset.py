import json
import boto3

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('cloudbelly-dev-housing-events')

def lambda_handler(event, context):
  datasetId = event["datasetId"]

  response = table.get_item(Key={'datasetId': datasetId})
  item = response.get('Item', {})

  return {
    'statusCode': 200,
    'headers': {'Content-Type': 'application/json'},
    'body': json.dumps(item)
  }
