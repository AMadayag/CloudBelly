import json
import logging
import boto3
import os
import statistics
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['TABLE_NAME'])


def lambda_handler(event, context):
    route = event.get("routeKey", "")
    logger.info(json.dumps({"event": "request_received", "route": route}))

    if route == "GET /api/v1/analytics/price-trend":
        return get_price_trend(event)
    elif route == "GET /api/v1/analytics/summary":
        return get_summary(event)
    else:
        logger.warning(json.dumps({"event": "route_not_found", "route": route}))
        return {'statusCode': 404, 'body': json.dumps('Not found')}


# GET /api/v1/analytics/summary


def get_summary(event):
    params = event.get("queryStringParameters") or {}
    multi_params = event.get("multiValueQueryStringParameters") or {}

    state = params.get("state", "NSW")
    suburbs = multi_params.get("suburb") or (
        [params.get("suburb")] if params.get("suburb") else None)

    if not suburbs:
        logger.warning(json.dumps({"event": "validation_error",
                       "route": "summary", "reason": "no suburb provided"}))
        return {'statusCode': 400, 'body': json.dumps({'error': 'At least one suburb is required'})}

    startDate = params.get("from")
    endDate = params.get("to")

    logger.info(json.dumps({
        "event": "summary_query",
        "state": state,
        "suburbs": suburbs,
        "from": startDate,
        "to": endDate
    }))

    try:
        items = []

        for suburb in suburbs:
            location = f"{state}#{suburb}"
            response = get_items(location, startDate, endDate)
            fetched = response.get('Items', [])
            logger.info(json.dumps({"event": "dynamodb_query",
                        "location": location, "items_returned": len(fetched)}))
            items.extend(fetched)

        # group prices by suburb
        suburb_prices = {}
        for item in items:
            s = item['state']
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
                "label": state,
                "data": data_points
            }]
        }

        logger.info(json.dumps({"event": "summary_success", "suburbs_returned": len(labels)}))

    except ClientError as e:
        logger.error(json.dumps({"event": "dynamodb_error", "route": "summary", "error": str(e)}))
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
    suburbs = multi_params.get("suburb") or (
        [params.get("suburb")] if params.get("suburb") else None)

    if not suburbs:
        logger.warning(json.dumps({"event": "validation_error",
                       "route": "price-trend", "reason": "no suburb provided"}))
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
            logger.info(json.dumps({"event": "dynamodb_query",
                        "location": location, "items_returned": len(items)}))

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
            "labels": state,
            "datasets": datasets
        }

        logger.info(json.dumps({"event": "price_trend_success",
                    "date_points": len(sorted_dates), "suburbs": len(datasets)}))

    except ClientError as e:
        logger.error(json.dumps({"event": "dynamodb_error",
                     "route": "price-trend", "error": str(e)}))
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
                KeyConditionExpression=Key('location').eq(location) & Key(
                    'eventKey').between(startDate, f"{endDate}#zzz")
            )
        elif startDate:
            response = table.query(
                KeyConditionExpression=(
                    Key('location').eq(location)
                    & Key('eventKey').gte(startDate)
                )
            )
        elif endDate:
            response = table.query(
                KeyConditionExpression=Key('location').eq(
                    location) & Key('eventKey').lte(f"{endDate}#zzz")
            )
        else:
            response = table.query(
                KeyConditionExpression=Key('location').eq(location)
            )
    except ClientError as e:
        logger.error(json.dumps({"event": "dynamodb_query_error",
                     "location": location, "error": str(e)}))
        raise RuntimeError(f"[FAIL] DynamoDB scan failed - {e}")

    response['Items'] = [parse_item(i) for i in response.get('Items', [])]
    return response


# flattens nested items


def parse_item(item):
    if 'date' in item and 'price' in item and 'suburb' in item:
        return item

    attrs = item.get('Attributes', {})
    timestamp = item.get('Time object', {}).get('timestamp', '')
    date = timestamp[:10] if timestamp else ''

    return {
        'date': date,
        'price': attrs.get('price'),
        'suburb': attrs.get('suburb'),
        'state': attrs.get('state'),
    }
