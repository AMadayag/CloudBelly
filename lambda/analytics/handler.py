import json
import boto3
import os
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
    multi_params = event.get("multiValueQueryStringParameters") or {}

    state = params.get("state", "NSW")
    suburbs = multi_params.get("suburb") or ([params.get("suburb")] if params.get("suburb") else None)

    if not suburbs:
        return {'statusCode': 400, 'body': json.dumps({'error': 'At least one suburb is required'})}

    startDate = params.get("from")
    endDate = params.get("to")

    try:
        items = []

        for suburb in suburbs:
            location = f"{state}#{suburb}"
            response = get_items(location, startDate, endDate)
            items.extend(response.get('Items', []))

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
            if len(prices) < 4:
                data_points.append({
                    "min": min(prices),
                    "q1": None,
                    "median": statistics.median(prices),
                    "q3": None,
                    "max": max(prices)
                })
            else:
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
                "label": f"{state} suburbs" if len(suburbs) > 1 else suburbs[0],
                "data": data_points
            }]
        }

    except ClientError as e:
        return {'statusCode': 500, 'body': json.dumps({'error': str(e)})}

    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps(data, default=str)
    }

# GET /api/v1/analytics/price-trend
def get_price_trend(event):
    params = event.get("queryStringParameters") or {}
    multi_params = event.get("multiValueQueryStringParameters") or {}

    state = params.get("state", "NSW")
    suburbs = multi_params.get("suburb") or ([params.get("suburb")] if params.get("suburb") else None)

    if not suburbs:
        return {'statusCode': 400, 'body': json.dumps({'error': 'At least one suburb is required'})}

    startDate = params.get("from")
    endDate = params.get("to")

    try:
        all_dates = set()
        suburb_price_maps = {}

        for suburb in suburbs:
            location = f"{state}#{suburb}"
            response = get_items(location, startDate, endDate)
            items = response.get('Items', [])

            price_map = {item['date']: item['price'] for item in items}
            suburb_price_maps[suburb] = price_map
            all_dates.update(price_map.keys())

        sorted_dates = sorted(all_dates)

        datasets = []
        for suburb in suburbs:
            price_map = suburb_price_maps[suburb]
            datasets.append({
                "label": suburb,
                "data": [price_map.get(date, None) for date in sorted_dates]
            })

        data = {
            "labels": sorted_dates,
            "datasets": datasets
        }

    except ClientError as e:
        return {'statusCode': 500, 'body': json.dumps({'error': str(e)})}

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