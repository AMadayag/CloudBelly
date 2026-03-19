import sys
import os
import json
import boto3
import pytest
from moto import mock_aws
from unittest.mock import patch

sys.path.append(os.path.abspath("lambda/analytics"))

TABLE_NAME = "cloudbelly-dev-housing-events"


@pytest.fixture(autouse=True)
def set_env():
    with patch.dict(os.environ, {
        "TABLE_NAME": TABLE_NAME,
        "STAGE": "dev"
    }):
        yield


@pytest.fixture
def dynamodb_table():
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

        # Insert test data
        items = [
            {"location": "Sydney#N/A", "eventKey": "2024-03-15#evt_001", "date": "2024-03-15", "state": "Sydney", "suburb": "N/A", "price": 950000},
            {"location": "Sydney#N/A", "eventKey": "2024-06-15#evt_002", "date": "2024-06-15", "state": "Sydney", "suburb": "N/A", "price": 1020000},
            {"location": "Sydney#N/A", "eventKey": "2024-09-15#evt_003", "date": "2024-09-15", "state": "Sydney", "suburb": "N/A", "price": 880000},
            {"location": "Sydney#N/A", "eventKey": "2024-12-15#evt_004", "date": "2024-12-15", "state": "Sydney", "suburb": "N/A", "price": 1100000},
        ]
        for item in items:
            table.put_item(Item=item)

        yield


# ── Unit Tests ──────────────────────────────────────────────────────────────

class TestPriceTrend:
    def test_missing_suburb_returns_400(self, dynamodb_table):
        from handler import lambda_handler
        response = lambda_handler({
            "routeKey": "GET /api/v1/analytics/price-trend",
            "queryStringParameters": {}
        }, None)
        assert response["statusCode"] == 400

    def test_price_trend_returns_200(self, dynamodb_table):
        from handler import lambda_handler
        response = lambda_handler({
            "routeKey": "GET /api/v1/analytics/price-trend",
            "queryStringParameters": {"suburb": "N/A", "state": "Sydney"}
        }, None)
        assert response["statusCode"] == 200

    def test_price_trend_response_structure(self, dynamodb_table):
        from handler import lambda_handler
        response = lambda_handler({
            "routeKey": "GET /api/v1/analytics/price-trend",
            "queryStringParameters": {"suburb": "N/A", "state": "Sydney"}
        }, None)
        body = json.loads(response["body"])
        assert "labels" in body
        assert "datasets" in body
        assert len(body["datasets"]) > 0
        assert "label" in body["datasets"][0]
        assert "data" in body["datasets"][0]

    def test_price_trend_returns_correct_count(self, dynamodb_table):
        from handler import lambda_handler
        response = lambda_handler({
            "routeKey": "GET /api/v1/analytics/price-trend",
            "queryStringParameters": {"suburb": "N/A", "state": "Sydney"}
        }, None)
        body = json.loads(response["body"])
        assert len(body["labels"]) == 4

    def test_price_trend_with_date_range(self, dynamodb_table):
        from handler import lambda_handler
        response = lambda_handler({
            "routeKey": "GET /api/v1/analytics/price-trend",
            "queryStringParameters": {
                "suburb": "N/A",
                "state": "Sydney",
                "from": "2024-03-01",
                "to": "2024-06-30"
            }
        }, None)
        body = json.loads(response["body"])
        assert len(body["labels"]) == 2

    def test_price_trend_empty_result(self, dynamodb_table):
        from handler import lambda_handler
        response = lambda_handler({
            "routeKey": "GET /api/v1/analytics/price-trend",
            "queryStringParameters": {"suburb": "N/A", "state": "Darwin"}
        }, None)
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["labels"] == []


class TestSummary:
    def test_missing_suburb_returns_400(self, dynamodb_table):
        from handler import lambda_handler
        response = lambda_handler({
            "routeKey": "GET /api/v1/analytics/summary",
            "queryStringParameters": {}
        }, None)
        assert response["statusCode"] == 400

    def test_summary_returns_200(self, dynamodb_table):
        from handler import lambda_handler
        response = lambda_handler({
            "routeKey": "GET /api/v1/analytics/summary",
            "queryStringParameters": {"suburb": "N/A", "state": "Sydney"}
        }, None)
        assert response["statusCode"] == 200

    def test_summary_response_structure(self, dynamodb_table):
        from handler import lambda_handler
        response = lambda_handler({
            "routeKey": "GET /api/v1/analytics/summary",
            "queryStringParameters": {"suburb": "N/A", "state": "Sydney"}
        }, None)
        body = json.loads(response["body"])
        assert "labels" in body
        assert "datasets" in body
        data_point = body["datasets"][0]["data"][0]
        assert "min" in data_point
        assert "max" in data_point
        assert "median" in data_point
        assert "q1" in data_point
        assert "q3" in data_point

    def test_summary_correct_min_max(self, dynamodb_table):
        from handler import lambda_handler
        response = lambda_handler({
            "routeKey": "GET /api/v1/analytics/summary",
            "queryStringParameters": {"suburb": "N/A", "state": "Sydney"}
        }, None)
        body = json.loads(response["body"])
        data_point = body["datasets"][0]["data"][0]
        assert data_point["min"] == 880000
        assert data_point["max"] == 1100000


class TestRouting:
    def test_unknown_route_returns_404(self, dynamodb_table):
        from handler import lambda_handler
        response = lambda_handler({"routeKey": "GET /unknown"}, None)
        assert response["statusCode"] == 404