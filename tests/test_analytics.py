import json
import os
import sys
import pytest
from unittest.mock import patch

sys.path.append(os.path.abspath("lambda"))


@pytest.fixture(autouse=True)
def set_env():
    with patch.dict(os.environ, {
        "TABLE_NAME": "mock-table",
        "AWS_DEFAULT_REGION": "us-east-1",
        "AWS_ACCESS_KEY_ID": "test",
        "AWS_SECRET_ACCESS_KEY": "test"
    }):
        yield


def build_event(route, params=None, multi_params=None):
    return {
        "routeKey": route,
        "queryStringParameters": params or {},
        "multiValueQueryStringParameters": multi_params or {}
    }


# Price summary
class TestGetSummary:
    @patch("analytics.handler.get_items")
    def test_summary_success_single_suburb(self, mock_get_items):
        mock_get_items.return_value = {
            "Items": [
                {"date": "2024-01-01", "price": "100",
                    "suburb": "Sydney", "state": "NSW"},
                {"date": "2024-01-02", "price": "200",
                    "suburb": "Sydney", "state": "NSW"},
                {"date": "2024-01-03", "price": "300",
                    "suburb": "Sydney", "state": "NSW"},
                {"date": "2024-01-04", "price": "400",
                    "suburb": "Sydney", "state": "NSW"},
            ]
        }

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

    @patch("analytics.handler.get_items")
    def test_summary_multiple_suburbs(self, mock_get_items):
        mock_get_items.side_effect = [
            {"Items": [
                {"date": "2024-01-01", "price": "100",
                    "suburb": "A", "state": "NSW"}
            ]},
            {"Items": [
                {"date": "2024-01-01", "price": "300",
                    "suburb": "B", "state": "NSW"}
            ]}
        ]

        from analytics.handler import lambda_handler

        event = build_event(
            "GET /api/v1/analytics/summary",
            {"state": "NSW"},
            {"suburb": ["A", "B"]}
        )

        response = lambda_handler(event, None)
        body = json.loads(response["body"])

        assert response["statusCode"] == 200
        assert len(body["datasets"][0]["data"]) == 1  # grouped by state
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
    @patch("analytics.handler.get_items")
    def test_price_trend_success(self, mock_get_items):
        mock_get_items.side_effect = [
            {
                "Items": [
                    {"date": "2024-01-01", "price": 100, "suburb": "A"},
                    {"date": "2024-01-02", "price": 200, "suburb": "A"},
                ]
            },
            {
                "Items": [
                    {"date": "2024-01-01", "price": 300, "suburb": "B"},
                ]
            }
        ]

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
        assert len(dates) == 2  # union of dates

    @patch("analytics.handler.get_items")
    def test_price_trend_handles_missing_dates(self, mock_get_items):
        mock_get_items.side_effect = [
            {"Items": [
                {"date": "2024-01-01", "price": 100, "suburb": "A"}
            ]},
            {"Items": [
                {"date": "2024-01-02", "price": 200, "suburb": "B"}
            ]}
        ]

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
