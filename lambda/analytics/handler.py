import json
import boto3
from botocore.exceptions import ClientError

def lambda_handler(event, context):
    route = event.get("routeKey", "")
  
  if route == "GET /api/v1/analytics/price-trend":
    return get_price_trend(event)
  else:
    return {'statusCode': 404, 'body': json.dumps('Not found')}

# GET /api/v1/analytics/price-trend
def get_price_trend(event):
    params = event.get("queryStringParameters")
    location = params.get("suburb")
    startDate = params.get("from")
    endDate = params.get("to")

    try:
    if startDate and endDate:
        response = table.query(
            KeyConditionExpression=Key('location').eq(location) & Key('date').between(startDate, endDate)
        )
    elif startDate:
        response = table.query(
            KeyConditionExpression=Key('location').eq(location) & Key('date').gte(startDate)
        )
    elif endDate:
        response = table.query(
            KeyConditionExpression=Key('location').eq(location) & Key('date').lte(endDate)
        )
    else:
        response = table.query(
            KeyConditionExpression=Key('location').eq(location)
        )

    items = response.get('Items', [])

    labels = [item['date'] for item in items]
    prices = [item['price'] for item in items]
    # may need to change from suburb to city if unable to access data
    suburb = items[0]['suburb'] if items else location

    data = {
        "labels": labels,
        "datasets": [{
            "label": suburb,
            "data": prices
        }]
    }

  except ClientError as e:
    raise RuntimeError(f"[FAIL] DynamoDB scan failed - {e}")

  return {
    'statusCode': 200,
    'headers': {'Content-Type': 'application/json'},
    'body': json.dumps(item, default=str)
  }
