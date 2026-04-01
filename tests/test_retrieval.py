import json
import os
import sys
import boto3
import pytest
from moto import mock_aws
from unittest.mock import patch

sys.path.append(os.path.abspath("lambda"))

TABLE_NAME = "cloudbelly-dev-housing-events"
DATASETS_TABLE_NAME = "cloudbelly-dev-datasets"


@pytest.fixture(autouse=True)
def set_env():
    with patch.dict(os.environ, {
        "TABLE_NAME": TABLE_NAME,
        "DATASETS_TABLE_NAME": DATASETS_TABLE_NAME,
        "AWS_DEFAULT_REGION": "us-east-1",
        "AWS_ACCESS_KEY_ID": "test",
        "AWS_SECRET_ACCESS_KEY": "test"
    }):
        yield


@pytest.fixture
def aws_resources():
    with mock_aws():
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")

        events_table = dynamodb.create_table(
            TableName=TABLE_NAME,
            KeySchema=[
                {"AttributeName": "location", "KeyType": "HASH"},
                {"AttributeName": "eventKey", "KeyType": "RANGE"}
            ],
            AttributeDefinitions=[
                {"AttributeName": "location", "AttributeType": "S"},
                {"AttributeName": "eventKey", "AttributeType": "S"}
            ],
            BillingMode="PAY_PER_REQUEST"
        )

        datasets_table = dynamodb.create_table(
            TableName=DATASETS_TABLE_NAME,
            KeySchema=[
                {"AttributeName": "datasetId", "KeyType": "HASH"}
            ],
            AttributeDefinitions=[
                {"AttributeName": "datasetId", "AttributeType": "S"}
            ],
            BillingMode="PAY_PER_REQUEST"
        )

        yield events_table, datasets_table


def build_event(route, params=None):
    return {
        "routeKey": route,
        "queryStringParameters": params or {}
    }


def put_event(table, suburb, state, date, price, event_id="evt-1",
              property_type="House", description="test", dataset_id="ds-1"):
    table.put_item(Item={
        "location": f"{state}#{suburb}",
        "eventKey": f"{date}#{event_id}",
        "eventId": event_id,
        "date": date,
        "state": state,
        "suburb": suburb,
        "price": price,
        "propertyType": property_type,
        "eventDescription": description,
        "datasetId": dataset_id
    })


def put_dataset(table, dataset_id, name, event_count, locations):
    table.put_item(Item={
        "datasetId": dataset_id,
        "name": name,
        "eventCount": event_count,
        "locations": locations
    })


# Events
class TestGetEvents:
    def test_get_events_returns_200(self, aws_resources):
        events_table, _ = aws_resources
        put_event(events_table, "Sydney", "NSW", "2024-01-01", 950000)

        import importlib
        import retrieval.handler as rh
        importlib.reload(rh)

        event = build_event(
            "GET /api/v1/events",
            {"suburb": "Sydney", "state": "NSW"}
        )
        response = rh.lambda_handler(event, None)

        assert response["statusCode"] == 200

    def test_get_events_returns_events_key(self, aws_resources):
        events_table, _ = aws_resources
        put_event(events_table, "Sydney", "NSW", "2024-01-01", 950000)

        import importlib
        import retrieval.handler as rh
        importlib.reload(rh)

        event = build_event(
            "GET /api/v1/events",
            {"suburb": "Sydney", "state": "NSW"}
        )
        response = rh.lambda_handler(event, None)
        body = json.loads(response["body"])

        assert "events" in body

    def test_get_events_returns_correct_data(self, aws_resources):
        events_table, _ = aws_resources
        put_event(
            events_table, "Sydney", "NSW", "2024-01-01", 950000,
            event_id="evt-42", property_type="House",
            description="test sale", dataset_id="ds-99"
        )

        import importlib
        import retrieval.handler as rh
        importlib.reload(rh)

        event = build_event(
            "GET /api/v1/events",
            {"suburb": "Sydney", "state": "NSW"}
        )
        response = rh.lambda_handler(event, None)
        body = json.loads(response["body"])
        evt = body["events"][0]

        assert evt["eventId"] == "evt-42"
        assert evt["timeObject"]["timestamp"] == "2024-01-01T00:00:00"
        assert evt["attributes"]["price"] == 950000.0
        assert evt["attributes"]["state"] == "NSW"
        assert evt["attributes"]["suburb"] == "Sydney"
        assert evt["attributes"]["propertyType"] == "House"
        assert evt["attributes"]["eventDescription"] == "test sale"
        assert evt["attributes"]["datasetId"] == "ds-99"

    def test_get_events_missing_suburb_returns_400(self, aws_resources):
        import importlib
        import retrieval.handler as rh
        importlib.reload(rh)

        event = build_event(
            "GET /api/v1/events",
            {"state": "NSW"}
        )
        response = rh.lambda_handler(event, None)

        assert response["statusCode"] == 400

    def test_get_events_no_params_returns_400(self, aws_resources):
        import importlib
        import retrieval.handler as rh
        importlib.reload(rh)

        event = build_event("GET /api/v1/events")
        response = rh.lambda_handler(event, None)

        assert response["statusCode"] == 400

    def test_get_events_with_date_filter(self, aws_resources):
        events_table, _ = aws_resources
        put_event(events_table, "Sydney", "NSW", "2023-06-01", 800000,
                  event_id="evt-old")
        put_event(events_table, "Sydney", "NSW", "2024-03-01", 950000,
                  event_id="evt-new")

        import importlib
        import retrieval.handler as rh
        importlib.reload(rh)

        event = build_event(
            "GET /api/v1/events",
            {
                "suburb": "Sydney",
                "state": "NSW",
                "startDate": "2024-01-01",
                "endDate": "2024-12-31"
            }
        )
        response = rh.lambda_handler(event, None)
        body = json.loads(response["body"])

        assert response["statusCode"] == 200
        assert len(body["events"]) == 1
        assert body["events"][0]["eventId"] == "evt-new"

    def test_get_events_nonexistent_suburb_returns_empty(self, aws_resources):
        import importlib
        import retrieval.handler as rh
        importlib.reload(rh)

        event = build_event(
            "GET /api/v1/events",
            {"suburb": "NoSuchPlace", "state": "NSW"}
        )
        response = rh.lambda_handler(event, None)
        body = json.loads(response["body"])

        assert response["statusCode"] == 200
        assert body["events"] == []


# Datasets
class TestGetDatasets:
    def test_get_datasets_returns_200(self, aws_resources):
        _, datasets_table = aws_resources
        put_dataset(datasets_table, "ds-1", "ABS Housing", 100,
                    ["NSW", "VIC"])

        import importlib
        import retrieval.handler as rh
        importlib.reload(rh)

        event = build_event("GET /api/v1/datasets")
        response = rh.lambda_handler(event, None)

        assert response["statusCode"] == 200

    def test_get_datasets_returns_datasets_key(self, aws_resources):
        _, datasets_table = aws_resources
        put_dataset(datasets_table, "ds-1", "ABS Housing", 100,
                    ["NSW", "VIC"])

        import importlib
        import retrieval.handler as rh
        importlib.reload(rh)

        event = build_event("GET /api/v1/datasets")
        response = rh.lambda_handler(event, None)
        body = json.loads(response["body"])

        assert "DataSets" in body

    def test_get_datasets_returns_correct_data(self, aws_resources):
        _, datasets_table = aws_resources
        put_dataset(datasets_table, "ds-abc", "ABS Housing", 250,
                    ["NSW", "VIC"])

        import importlib
        import retrieval.handler as rh
        importlib.reload(rh)

        event = build_event("GET /api/v1/datasets")
        response = rh.lambda_handler(event, None)
        body = json.loads(response["body"])

        assert len(body["DataSets"]) == 1
        ds = body["DataSets"][0]
        assert ds["datasetId"] == "ds-abc"
        assert ds["name"] == "ABS Housing"
        assert int(ds["eventCount"]) == 250


# Router
class TestLambdaHandler:
    def test_unknown_route_returns_404(self, aws_resources):
        import importlib
        import retrieval.handler as rh
        importlib.reload(rh)

        event = build_event("GET /api/v1/unknown")
        response = rh.lambda_handler(event, None)

        assert response["statusCode"] == 404
