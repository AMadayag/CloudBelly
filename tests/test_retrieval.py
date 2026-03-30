import sys
import os
import json
import boto3
import pytest
from moto import mock_aws
from unittest.mock import patch

sys.path.append(os.path.abspath("lambda/retrieval"))

TABLE_NAME = "cloudbelly-dev-housing-events"
DATASETS_TABLE_NAME = "cloudbelly-dev-datasets"


@pytest.fixture(autouse=True)
def set_env():
    with patch.dict(os.environ, {
        "TABLE_NAME": TABLE_NAME,
        "DATASETS_TABLE_NAME": DATASETS_TABLE_NAME,
        "STAGE": "dev"
    }):
        yield


@pytest.fixture
def dynamodb_tables():
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

        events_table.put_item(Item={
            "location": "Sydney#N/A",
            "eventKey": "2024-03-15#evt_001",
            "eventId": "evt_001",
            "date": "2024-03-15",
            "state": "Sydney",
            "suburb": "N/A",
            "price": 950000,
            "property": "house"
        })
        events_table.put_item(Item={
            "location": "Sydney#N/A",
            "eventKey": "2024-06-15#evt_002",
            "eventId": "evt_002",
            "date": "2024-06-15",
            "state": "Sydney",
            "suburb": "N/A",
            "price": 1020000,
            "property": "attached_dwelling"
        })
        events_table.put_item(Item={
            "location": "Brisbane#N/A",
            "eventKey": "2024-03-15#evt_003",
            "eventId": "evt_003",
            "date": "2024-03-15",
            "state": "Brisbane",
            "suburb": "N/A",
            "price": 750000,
            "property": "house"
        })

        datasets_table.put_item(Item={
            "datasetId": "ds_001",
            "name": "ABS Total Value of Dwellings",
            "datasource": "www.abs.gov.au",
            "locations": ["Sydney", "Brisbane"],
            "eventCount": "3"
        })

        yield


class TestGetEvents:
    def test_missing_suburb_returns_400(self, dynamodb_tables):
        from handler import lambda_handler
        response = lambda_handler(
            {
                "routeKey": "GET /api/v1/events",
                "queryStringParameters": {},
            },
            None,
        )
        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "error" in body

    def test_get_events_with_state(self, dynamodb_tables):
        from handler import lambda_handler
        event = {
            "routeKey": "GET /api/v1/events",
            "queryStringParameters": {"suburb": "N/A", "state": "Sydney"}
        }
        response = lambda_handler(event, None)
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert "events" in body
        assert len(body["events"]) == 2

    def test_get_events_without_state_scans(self, dynamodb_tables):
        from handler import lambda_handler
        event = {
            "routeKey": "GET /api/v1/events",
            "queryStringParameters": {"suburb": "N/A"}
        }
        response = lambda_handler(event, None)
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert "events" in body
        assert len(body["events"]) >= 1

    def test_get_events_with_date_range(self, dynamodb_tables):
        from handler import lambda_handler
        event = {
            "routeKey": "GET /api/v1/events",
            "queryStringParameters": {
                "suburb": "N/A",
                "state": "Sydney",
                "startDate": "2024-03-01",
                "endDate": "2024-04-01"
            }
        }
        response = lambda_handler(event, None)
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert len(body["events"]) == 1

    def test_get_events_with_min_price(self, dynamodb_tables):
        from handler import lambda_handler
        event = {
            "routeKey": "GET /api/v1/events",
            "queryStringParameters": {
                "suburb": "N/A",
                "state": "Sydney",
                "minPrice": "1000000"
            }
        }
        response = lambda_handler(event, None)
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert all(e["attributes"]["price"] >= 1000000 for e in body["events"])

    def test_get_events_with_max_price(self, dynamodb_tables):
        from handler import lambda_handler
        event = {
            "routeKey": "GET /api/v1/events",
            "queryStringParameters": {
                "suburb": "N/A",
                "state": "Sydney",
                "maxPrice": "960000"
            }
        }
        response = lambda_handler(event, None)
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert all(e["attributes"]["price"] <= 960000 for e in body["events"])

    def test_event_response_structure(self, dynamodb_tables):
        from handler import lambda_handler
        event = {
            "routeKey": "GET /api/v1/events",
            "queryStringParameters": {"suburb": "N/A", "state": "Sydney"}
        }
        response = lambda_handler(event, None)
        body = json.loads(response["body"])
        evt = body["events"][0]
        assert "eventId" in evt
        assert "eventType" in evt
        assert "timeObject" in evt
        assert "locations" in evt
        assert "attributes" in evt


class TestGetDatasets:
    def test_get_datasets_returns_200(self, dynamodb_tables):
        from handler import lambda_handler
        response = lambda_handler({"routeKey": "GET /api/v1/datasets"}, None)
        assert response["statusCode"] == 200

    def test_get_datasets_returns_datasets_key(self, dynamodb_tables):
        from handler import lambda_handler
        response = lambda_handler({"routeKey": "GET /api/v1/datasets"}, None)
        body = json.loads(response["body"])
        assert "DataSets" in body

    def test_get_datasets_returns_correct_data(self, dynamodb_tables):
        from handler import lambda_handler
        response = lambda_handler({"routeKey": "GET /api/v1/datasets"}, None)
        body = json.loads(response["body"])
        assert len(body["DataSets"]) == 1
        assert body["DataSets"][0]["datasource"] == "www.abs.gov.au"


class TestRouting:
    def test_unknown_route_returns_404(self, dynamodb_tables):
        from handler import lambda_handler
        response = lambda_handler({"routeKey": "GET /unknown"}, None)
        assert response["statusCode"] == 404
