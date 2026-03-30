import json
import os
import boto3
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key, Attr

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['TABLE_NAME'])
datasets_table = boto3.resource('dynamodb').Table(os.environ[
                                                        'DATASETS_TABLE_NAME'])


def lambda_handler(event, context):
    route = event.get("routeKey", "")

    if route == "GET /api/v1/events":
        return get_events(event)
    elif route == "GET /api/v1/datasets":
        return get_datasets(event)
    else:
        return {'statusCode': 404, 'body': json.dumps('Not found')}


# GET /api/v1/events
def get_events(event):
    params = event.get("queryStringParameters") or {}
    suburb = params.get("suburb")

    if not suburb:
        return {
            'statusCode': 400,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({"error": "suburb is required"})
        }

    state = params.get("state")
    start_date = params.get("startDate")
    end_date = params.get("endDate")
    min_price = params.get("minPrice")
    max_price = params.get("maxPrice")

    try:
        if state:
            location = f"{state}#{suburb}"
            key_condition = Key('location').eq(location)
            if start_date and end_date:
                key_condition &= Key('eventKey').between(
                    start_date, f"{end_date}#zzz"
                )
            elif start_date:
                key_condition &= Key('eventKey').gte(start_date)
            elif end_date:
                key_condition &= Key('eventKey').lte(f"{end_date}#zzz")

            filter_expr = None
            if min_price and max_price:
                filter_expr = Attr('price').between(
                                                int(min_price), int(max_price))
            elif min_price:
                filter_expr = Attr('price').gte(int(min_price))
            elif max_price:
                filter_expr = Attr('price').lte(int(max_price))

            query_kwargs = {'KeyConditionExpression': key_condition}
            if filter_expr:
                query_kwargs['FilterExpression'] = filter_expr

            response = table.query(**query_kwargs)
            items = response.get('Items', [])

        else:
            # no state provided: scanning all states for the given suburb
            filter_expr = Attr('suburb').eq(suburb)
            if start_date and end_date:
                filter_expr &= Attr('date').between(start_date, end_date)
            elif start_date:
                filter_expr &= Attr('date').gte(start_date)
            elif end_date:
                filter_expr &= Attr('date').lte(end_date)

            if min_price and max_price:
                filter_expr &= Attr('price').between(
                                                int(min_price), int(max_price))
            elif min_price:
                filter_expr &= Attr('price').gte(int(min_price))
            elif max_price:
                filter_expr &= Attr('price').lte(int(max_price))

            response = table.scan(FilterExpression=filter_expr)
            items = response.get('Items', [])

        events = [
            {
                "eventId": item.get("eventId"),
                "eventType": item.get("eventType", "property-sale"),
                "timeObject": {
                    "timestamp": f"{item.get('date')}T00:00:00",
                    "duration": item.get("duration", 0),
                    "timezone": item.get("timezone", "Australia/Sydney")
                },
                "locations": [item.get("state")],
                "attributes": {
                    "price": float(item.get("price") or 0),
                    "city": item.get("state"),
                    "propertyType": item.get("property")
                }
            }
            for item in items
        ]
    except ClientError as e:
        raise RuntimeError(f"[FAIL] DynamoDB query failed - {e}")

    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps({"events": events}, default=str)
    }


# GET /api/v1/datasets
def get_datasets(_event):
    try:
        response = datasets_table.scan()
        datasets = response.get('Items', [])
    except ClientError as e:
        raise RuntimeError(f"[FAIL] DynamoDB scan failed - {e}")

    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps({"DataSets": datasets}, default=str)
    }
