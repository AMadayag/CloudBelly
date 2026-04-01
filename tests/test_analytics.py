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
BUCKET_NAME = "cloudbelly-team-dev-raw-events"


@pytest.fixture(autouse=True)
def set_env():
    with patch.dict(os.environ, {
        "TABLE_NAME": TABLE_NAME,
        "DATASETS_TABLE_NAME": DATASETS_TABLE_NAME,
        "BUCKET_NAME": BUCKET_NAME,
        "STAGE": "dev",
        "AWS_DEFAULT_REGION": "us-east-1",
        "AWS_REGION": "us-east-1"
    }):
        yield


@pytest.fixture
def aws_resources():
    with mock_aws():
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        table = dynamodb.create_table(
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

        yield table


def build_event(route, params=None, multi_params=None):
    return {
        "routeKey": route,
        "queryStringParameters": params or {},
        "multiValueQueryStringParameters": multi_params or {}
    }


def put_event(table, suburb, state, date, price):
    table.put_item(Item={
        "location": f"{state}#{suburb}",
        "eventKey": date,
        "date": date,
        "price": price,
        "suburb": suburb,
        "state": state
    })


# Price summary
class TestGetSummary:
    def test_summary_success_single_suburb(self, aws_resources):
        table = aws_resources

        put_event(table, "Sydney", "NSW", "2024-01-01", 100)
        put_event(table, "Sydney", "NSW", "2024-01-02", 200)
        put_event(table, "Sydney", "NSW", "2024-01-03", 300)
        put_event(table, "Sydney", "NSW", "2024-01-04", 400)

        from analytics.handler import lambda_handler

        event = build_event(
            "GET /api/v1/analytics/summary",
            {"state": "NSW", "suburb": "Sydney"}
        )

        response = lambda_handler(event, None)
        body = json.loads(response["body"])

        assert response["statusCode"] == 200
        assert body["labels"] == ["NSW"]
        assert len(body["datasets"][0]["data"]) == 1

        data = body["datasets"][0]["data"][0]
        assert data["min"] == 100
        assert data["max"] == 400
        assert data["median"] == 250

    def test_summary_multiple_suburbs(self, aws_resources):
        table = aws_resources

        put_event(table, "A", "NSW", "2024-01-01", 100)
        put_event(table, "B", "NSW", "2024-01-01", 300)

        from analytics.handler import lambda_handler

        event = build_event(
            "GET /api/v1/analytics/summary",
            {"state": "NSW"},
            {"suburb": ["A", "B"]}
        )

        response = lambda_handler(event, None)
        body = json.loads(response["body"])

        assert response["statusCode"] == 200
        # grouped by state
        assert len(body["datasets"][0]["data"]) == 1
        assert body["labels"] == ["NSW"]

    def test_summary_missing_suburb_returns_400(self):
        from analytics.handler import lambda_handler

        event = build_event(
            "GET /api/v1/analytics/summary",
            {"state": "NSW"}
        )

        response = lambda_handler(event, None)

        assert response["statusCode"] == 400


# Price trend
class TestPriceTrend:
    def test_price_trend_success(self, aws_resources):
        table = aws_resources

        put_event(table, "A", "NSW", "2024-01-01", 100)
        put_event(table, "A", "NSW", "2024-01-02", 200)
        put_event(table, "B", "NSW", "2024-01-01", 300)

        from analytics.handler import lambda_handler

        event = build_event(
            "GET /api/v1/analytics/price-trend",
            {"state": "NSW"},
            {"suburb": ["A", "B"]}
        )

        response = lambda_handler(event, None)
        body = json.loads(response["body"])

        assert response["statusCode"] == 200
        assert len(body["datasets"]) == 2

        dates = body["datasets"][0]["data"]
        # union of dates
        assert len(dates) == 2

    def test_price_trend_handles_missing_dates(self, aws_resources):
        table = aws_resources

        put_event(table, "A", "NSW", "2024-01-01", 100)
        put_event(table, "B", "NSW", "2024-01-02", 200)

        from analytics.handler import lambda_handler

        event = build_event(
            "GET /api/v1/analytics/price-trend",
            {},
            {"suburb": ["A", "B"]}
        )

        response = lambda_handler(event, None)
        body = json.loads(response["body"])

        dataset_a = body["datasets"][0]["data"]
        dataset_b = body["datasets"][1]["data"]

        assert dataset_a != dataset_b
        assert None in dataset_a or None in dataset_b

    def test_price_trend_missing_suburb_returns_400(self):
        from analytics.handler import lambda_handler

        event = build_event(
            "GET /api/v1/analytics/price-trend",
            {"state": "NSW"}
        )

        response = lambda_handler(event, None)

        assert response["statusCode"] == 400


# Router
class TestLambdaHandler:
    def test_unknown_route_returns_404(self):
        from analytics.handler import lambda_handler

        event = build_event("GET /unknown")

        response = lambda_handler(event, None)

        assert response["statusCode"] == 404
