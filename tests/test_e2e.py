# tests/test_e2e.py
import sys
import os
import json
import boto3
import pytest
from moto import mock_aws
from unittest.mock import patch

sys.path.append(os.path.abspath("lambda"))
sys.path.append(os.path.abspath("lambda/collection"))

TABLE_NAME = "cloudbelly-dev-housing-events"
DATASETS_TABLE_NAME = "cloudbelly-dev-datasets"
BUCKET_NAME = "cloudbelly-team-dev-raw-events"


@pytest.fixture(autouse=True)
def set_env():
    with patch.dict(os.environ, {
        "TABLE_NAME": TABLE_NAME,
        "DATASETS_TABLE_NAME": DATASETS_TABLE_NAME,
        "BUCKET_NAME": BUCKET_NAME,
        "AWS_REGION": "us-east-1",
        "AWS_DEFAULT_REGION": "us-east-1"
    }):
        yield


@pytest.fixture(autouse=True)
def reset_analytics_table():
    import analytics.handler as ah
    ah.table = None
    yield
    ah.table = None


@pytest.fixture
def aws_resources():
    with mock_aws():
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")

        dynamodb.create_table(
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

        dynamodb.create_table(
            TableName=DATASETS_TABLE_NAME,
            KeySchema=[{"AttributeName": "datasetId", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "datasetId",
                                  "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST"
        )

        # S3 will be mocked via mock_aws as well
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket=BUCKET_NAME)

        yield dynamodb


class MockScraper:
    def getName(self):
        return "total_value_of_dwellings"

    def getDomain(self):
        return "www.abs.gov.au"

    def setPipeline(self, pipeline):
        self.pipeline = pipeline

    def start(self):
        # simulate a scraped dataset
        self.pipeline.processItem({
            "date": "2024-01-01",
            "area": "NSW",
            "median_price_of_established_house_transfers": 100,
            "median_price_of_attached_dwelling_transfers": 200,
        })
        self.pipeline.processItem({
            "date": "2024-01-02",
            "area": "NSW",
            "median_price_of_established_house_transfers": 300,
            "median_price_of_attached_dwelling_transfers": 400,
        })


def test_full_e2e_flow(aws_resources):
    from collection.handler import lambda_handler as collection_handler
    from analytics.handler import lambda_handler as analytics_handler
    from retrieval.handler import lambda_handler as retrieval_handler

    # collection run
    with patch(
        "collection.handler.TotalValueOfDwellingsScraper",
        return_value=MockScraper()
    ):
        response = collection_handler({}, None)
    assert response["statusCode"] == 200

    # summary
    summary_event = {
        "routeKey": "GET /api/v1/analytics/summary",
        "queryStringParameters": {"state": "NSW", "suburb": "N/A"},
        "multiValueQueryStringParameters": {}
    }
    response = analytics_handler(summary_event, None)
    body = json.loads(response["body"])
    assert response["statusCode"] == 200
    assert body["labels"] == ["NSW"]
    assert len(body["datasets"][0]["data"]) == 1

    # price trend
    trend_event = {
        "routeKey": "GET /api/v1/analytics/price-trend",
        "queryStringParameters": {"state": "NSW", "suburb": "N/A"},
        "multiValueQueryStringParameters": {}
    }
    response = analytics_handler(trend_event, None)
    body = json.loads(response["body"])
    assert response["statusCode"] == 200
    assert len(body["datasets"]) == 1
    assert len(body["datasets"][0]["data"]) == 2

    # events with date filter
    events_event = {
        "routeKey": "GET /api/v1/events",
        "queryStringParameters": {
            "state": "NSW",
            "suburb": "N/A",
            "startDate": "2024-01-01",
            "endDate": "2024-01-01"
        }
    }
    response = retrieval_handler(events_event, None)
    body = json.loads(response["body"])
    assert response["statusCode"] == 200
    assert len(body["events"]) >= 1
    for event in body["events"]:
        assert event["timeObject"]["timestamp"].startswith("2024-01-01")


def test_e2e_multiple_suburbs(aws_resources):
    from collection.handler import lambda_handler as collection_handler
    from analytics.handler import lambda_handler as analytics_handler
    from retrieval.handler import lambda_handler as retrieval_handler

    class MultiScraper:
        def getName(self): return "total_value_of_dwellings"
        def getDomain(self): return "www.abs.gov.au"

        def setPipeline(self, pipeline):
            self.pipeline = pipeline

        def start(self):
            # Two different dates for NSW, to test price trend has 2 points
            self.pipeline.processItem({
                "date": "2024-01-01",
                "area": "NSW",
                "median_price_of_established_house_transfers": 100,
                "median_price_of_attached_dwelling_transfers": 200,
            })
            self.pipeline.processItem({
                "date": "2024-02-01",
                "area": "NSW",
                "median_price_of_established_house_transfers": 300,
                "median_price_of_attached_dwelling_transfers": 400,
            })
            # VIC data on same dates
            self.pipeline.processItem({
                "date": "2024-01-01",
                "area": "VIC",
                "median_price_of_established_house_transfers": 500,
                "median_price_of_attached_dwelling_transfers": None,
            })
            self.pipeline.processItem({
                "date": "2024-02-01",
                "area": "VIC",
                "median_price_of_established_house_transfers": 600,
                "median_price_of_attached_dwelling_transfers": None,
            })

    with patch(
        "collection.handler.TotalValueOfDwellingsScraper",
        return_value=MultiScraper()
    ):
        response = collection_handler({}, None)
    assert response["statusCode"] == 200

    # summary: single state, single suburb
    for state in ["NSW", "VIC"]:
        summary_event = {
            "routeKey": "GET /api/v1/analytics/summary",
            "queryStringParameters": {"state": state},
            "multiValueQueryStringParameters": {"suburb": ["N/A"]}
        }
        response = analytics_handler(summary_event, None)
        body = json.loads(response["body"])
        assert response["statusCode"] == 200
        assert state in body["labels"]
        assert len(body["datasets"][0]["data"]) == 1

    # price trend: single state, verifies multiple date points
    for state in ["NSW", "VIC"]:
        trend_event = {
            "routeKey": "GET /api/v1/analytics/price-trend",
            "queryStringParameters": {"state": state},
            "multiValueQueryStringParameters": {"suburb": ["N/A"]}
        }
        response = analytics_handler(trend_event, None)
        body = json.loads(response["body"])
        assert response["statusCode"] == 200
        assert len(body["datasets"]) == 1
        assert len(body["datasets"][0]["data"]) == 2

    # retrieval: date filter returns only matching events
    for state in ["NSW", "VIC"]:
        events_event = {
            "routeKey": "GET /api/v1/events",
            "queryStringParameters": {
                "state": state,
                "suburb": "N/A",
                "startDate": "2024-01-01",
                "endDate": "2024-01-01"
            }
        }
        response = retrieval_handler(events_event, None)
        body = json.loads(response["body"])
        assert response["statusCode"] == 200
        assert len(body["events"]) >= 1
        for event in body["events"]:
            assert event["timeObject"]["timestamp"].startswith("2024-01-01")
