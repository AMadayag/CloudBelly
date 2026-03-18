import json
import boto3
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key, Attr

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table = dynamodb.Table('cloudbelly-dev-housing-events')

def lambda_handler(event, context):
  route = event.get("routeKey", "")

  if route == "GET /api/v1/events":
    return get_events(event)
  elif route == "GET /api/v1/datasets":
    return get_datasets(event)
  elif route == "GET /api/v1/datasets/{datasetId}":
    return get_dataset_by_id(event)
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
        key_condition &= Key('eventKey').between(start_date, f"{end_date}#zzz")
      elif start_date:
        key_condition &= Key('eventKey').gte(start_date)
      elif end_date:
        key_condition &= Key('eventKey').lte(f"{end_date}#zzz")

      filter_expr = None
      if min_price and max_price:
        filter_expr = Attr('price').between(int(min_price), int(max_price))
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
      # no state provided : scanning all states for the given suburb
      filter_expr = Attr('suburb').eq(suburb)
      if start_date and end_date:
        filter_expr &= Attr('date').between(start_date, end_date)
      elif start_date:
        filter_expr &= Attr('date').gte(start_date)
      elif end_date:
        filter_expr &= Attr('date').lte(end_date)

      if min_price and max_price:
        filter_expr &= Attr('price').between(int(min_price), int(max_price))
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
        "locations": [item.get("suburb"), item.get("state")],
        "attributes": {
          "price": float(item.get("price", 0)),
          "suburb": item.get("suburb"),
          "state": item.get("state"),
          "address": item.get("address"),
          "propertyType": item.get("propertyType")
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
    response = table.scan()
    items = response.get('Items', [])

    # grouping events by sourceFileKey (each file = one dataset)
    datasets = {}
    for item in items:
      source = item.get('sourceFileKey', 'unknown')
      if source not in datasets:
        datasets[source] = {
          "Datasource": item.get('datasource', ''),
          "Data set type": item.get('datasetType', ''),
          "Dataset ID": f"s3::{source}",
          "Time object": {
            "timestamp": item.get('ingestedAt', ''),
            "timezone": item.get('timezone', '')
          },
          "Locations": [],
          "Events": []
        }

      state = item.get('state', '')
      suburb = item.get('suburb', '')
      if state not in datasets[source]["Locations"]:
        datasets[source]["Locations"].append(state)

      datasets[source]["Events"].append({
        "Event ID": item.get('eventId'),
        "Event type": item.get("eventType", "property-sale"),
        "Time object": {
          "timestamp": f"{item.get('date')}T00:00:00",
          "duration": item.get("duration", 0),
          "timezone": item.get("timezone", "Australia/Sydney")
        },
        "Locations": [suburb, state],
        "Attributes": {
          "price": float(item.get('price', 0)),
          "suburb": suburb,
          "state": state,
          "address": item.get('address'),
          "propertyType": item.get('propertyType')
        }
      })

  except ClientError as e:
    raise RuntimeError(f"[FAIL] DynamoDB scan failed - {e}")

  return {
    'statusCode': 200,
    'headers': {'Content-Type': 'application/json'},
    'body': json.dumps({"DataSets": list(datasets.values())}, default=str)
  }


# GET /api/v1/datasets/{datasetId}
def get_dataset_by_id(event):
  try:
    datasetId = event["pathParameters"]["datasetId"]
    response = table.scan(
        FilterExpression=Attr('data').eq(datasetId)
    )
    items = response.get('Items', []) or {}
    item = items[0] if items else {}
  except ClientError as e:
    raise RuntimeError(f"[FAIL] DynamoDB scan failed - {e}")

  return {
    'statusCode': 200,
    'headers': {'Content-Type': 'application/json'},
    'body': json.dumps(item, default=str)
  }
