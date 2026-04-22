import json
import logging
import os
import boto3
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key, Attr

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['TABLE_NAME'])
datasets_table = boto3.resource('dynamodb').Table(os.environ[
                                                        'DATASETS_TABLE_NAME'])


def lambda_handler(event, context):
    route = event.get("routeKey", "")
    logger.info(json.dumps({"event": "request_received", "route": route}))

    if route == "GET /api/v1/events":
        return get_events(event)
    elif route == "GET /api/v1/datasets":
        return get_datasets(event)
    elif route == "GET /api/v1/events/recent":
        return get_recent_events(event)
    else:
        logger.warning(json.dumps(
                            {"event": "route_not_found", "route": route}))
        return {'statusCode': 404, 'body': json.dumps('Not found'),
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'}}


# GET /api/v1/events
def get_events(event):
    params = event.get("queryStringParameters") or {}
    suburb = params.get("suburb")

    if not suburb:
        logger.warning(json.dumps({"event": "validation_error",
                       "route": "events", "reason": "no suburb provided"}))
        return {
            'statusCode': 400,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({"error": "suburb is required"})
        }

    state = params.get("state")
    start_date = params.get("startDate")
    end_date = params.get("endDate")
    min_price = params.get("minPrice")
    max_price = params.get("maxPrice")

    logger.info(json.dumps({
        "event": "events_query",
        "suburb": suburb,
        "state": state,
        "start_date": start_date,
        "end_date": end_date,
        "min_price": min_price,
        "max_price": max_price
    }))

    try:
        if state:
            location = f"{state}#{suburb}"
            key_condition = Key('location').eq(location)
            if start_date and end_date:
                key_condition &= Key('eventKey').between(
                                                start_date, f"{end_date}#zzz")
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
            logger.info(json.dumps({"event": "dynamodb_query",
                        "location": location, "items_returned": len(items)}))

        else:
            logger.info(json.dumps(
                    {"event": "full_scan", "reason": "no state provided",
                        "suburb": suburb}))
            # no state provided : scanning all states for the given suburb
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
            logger.info(json.dumps(
                    {"event": "dynamodb_scan", "items_returned": len(items)}))

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
                    "state": item.get("state"),
                    "suburb": item.get("suburb"),
                    "propertyType": item.get("property"),
                    "eventDescription": item.get("eventDescription"),
                    "datasetId": item.get("datasetId"),
                    "postcode": item.get("postcode"),
                    "streetName": item.get("streetName"),
                    "houseNumber": item.get("houseNumber"),
                    "natureOfProperty": item.get("natureOfProperty"),
                    "zoning": item.get("zoning"),
                    "area": item.get("area"),
                    "contractDate": item.get("contractDate"),
                    "legalDescription": item.get("legalDescription"),
                }
            }
            for item in items
        ]
        logger.info(json.dumps(
            {"event": "events_success", "events_returned": len(events)}))
    except ClientError as e:
        logger.error(json.dumps(
            {"event": "dynamodb_error", "route": "events", "error": str(e)}))
        raise RuntimeError(f"[FAIL] DynamoDB query failed - {e}")

    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
        'body': json.dumps({"events": events}, default=str)
    }


# GET /api/v1/datasets
def get_datasets(_event):
    logger.info(json.dumps({"event": "datasets_query"}))
    try:
        response = datasets_table.scan()
        datasets = response.get('Items', [])
        logger.info(json.dumps(
            {"event": "datasets_success", "datasets_returned": len(datasets)}))
    except ClientError as e:
        logger.error(json.dumps(
            {"event": "dynamodb_error", "route": "datasets", "error": str(e)}))
        raise RuntimeError(f"[FAIL] DynamoDB scan failed - {e}")

    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
        'body': json.dumps({"DataSets": datasets}, default=str)
    }


# GET /api/v1/events/recent
def get_recent_events(event):
    params = event.get("queryStringParameters") or {}
    suburb = params.get("suburb")
    state = params.get("state")

    if not suburb or not state:
        return {
            'statusCode': 400,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({"error": "suburb and state are required"})
        }

    location = f"{state}#{suburb}"

    try:
        response = table.query(
            KeyConditionExpression=Key('location').eq(location),
            ScanIndexForward=False,
            Limit=10
        )
        items = response.get('Items', [])

        events = [
            {
                "eventId": item.get("eventId"),
                "date": item.get("date"),
                "price": float(item.get("price") or 0),
                "suburb": item.get("suburb"),
                "state": item.get("state"),
                "propertyType": item.get("property"),
                "streetName": item.get("streetName"),
                "houseNumber": item.get("houseNumber"),
                "postcode": item.get("postcode"),
            }
            for item in items
        ]

    except ClientError as e:
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({"error": str(e)})
        }

    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
        'body': json.dumps({"events": events}, default=str)
    }
