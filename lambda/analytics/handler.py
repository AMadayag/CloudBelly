import json
import boto3
import statistics
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['TABLE_NAME'])

def lambda_handler(event, context):
    route = event.get("routeKey", "")
  
    if route == "GET /api/v1/analytics/price-trend":
        return get_price_trend(event)
    elif route == "GET /api/v1/analytics/summary":
        return get_summary(event)
    else:
    return {'statusCode': 404, 'body': json.dumps('Not found')}

# GET /api/v1/analytics/summary
def get_summary(event):
    params = event.get("queryStringParameters") or {}
    state = params.get("state", "NSW")
    location = f"{state}#{params.get('suburb')}"
    startDate = params.get("from")
    endDate = params.get("to")

    try:
        response = get_items(location, startDate, endDate)
        items = response.get('Items', [])

        # group prices by suburb
        suburb_prices = {}
        for item in items:
            s = item['suburb']
            if s not in suburb_prices:
                suburb_prices[s] = []
            suburb_prices[s].append(float(item['price']))

        labels = list(suburb_prices.keys())
        data_points = []
        for s in labels:
            prices = sorted(suburb_prices[s])
            data_points.append({
                "min": min(prices),
                "q1": statistics.quantiles(prices, n=4)[0],
                "median": statistics.median(prices),
                "q3": statistics.quantiles(prices, n=4)[2],
                "max": max(prices)
            })

        data = {
            "labels": labels,
            "datasets": [{
                "label": location,
                "data": data_points
            }]
        }

    except ClientError as e:
        raise RuntimeError(f"[FAIL] DynamoDB scan failed - {e}")

    return {
    'statusCode': 200,
    'headers': {'Content-Type': 'application/json'},
    'body': json.dumps(data, default=str)
    }

# GET /api/v1/analytics/price-trend
def get_price_trend(event):
    params = event.get("queryStringParameters") or {}
    location = params.get("suburb")
    startDate = params.get("from")
    endDate = params.get("to")

    try:
        response = get_items(location, startDate, endDate)
        items = response.get('Items', [])

        labels = [item['eventKey'] for item in items]
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
        'body': json.dumps(data, default=str)
    }

# gets items with optional start and end date params
def get_items(location, startDate, endDate):
    try:
        if startDate and endDate:
            response = table.query(
                KeyConditionExpression=Key('location').eq(location) & Key('eventKey').between(startDate, f"{endDate}#zzz")
            )
        elif startDate:
            response = table.query(
                KeyConditionExpression=Key('location').eq(location) & Key('eventKey').gte(startDate)
            )
        elif endDate:
            response = table.query(
                KeyConditionExpression=Key('location').eq(location) & Key('eventKey').lte(f"{endDate}#zzz")
            )
        else:
            response = table.query(
                KeyConditionExpression=Key('location').eq(location)
            )
    except ClientError as e:
        raise RuntimeError(f"[FAIL] DynamoDB scan failed - {e}")
    
    return response
