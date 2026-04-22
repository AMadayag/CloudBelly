"""
Integration tests:  retrival
"""
import importlib
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
        "AWS_ACCESS_KEY_ID": "test",
        "AWS_SECRET_ACCESS_KEY": "test"
    }):
        yield


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
            KeySchema=[
                {"AttributeName": "datasetId", "KeyType": "HASH"}
            ],
            AttributeDefinitions=[
                {"AttributeName": "datasetId", "AttributeType": "S"}
            ],
            BillingMode="PAY_PER_REQUEST"
        )

        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket=BUCKET_NAME)

        yield dynamodb


def run_pipeline(area="New South Wales", date="2024-01-01",
                 house_price=950000, dwelling_price=750000):
    """Run the real collection pipeline to seed data."""
    from collection.collection.pipelines import TotalValueOfDwellingsPipeline
    pipeline = TotalValueOfDwellingsPipeline(
        "total_value_of_dwellings", "www.abs.gov.au", BUCKET_NAME
    )
    pipeline.processItem({
        "date": date,
        "area": area,
        "median_price_of_established_house_transfers": house_price,
        "median_price_of_attached_dwelling_transfers": dwelling_price,
        "number_of_established_house_transfers": 100,
        "number_of_attached_dwelling_transfers": 50
    })
    pipeline.finish()


def build_event(route, params=None):
    return {
        "routeKey": route,
        "queryStringParameters": params or {}
    }


def get_retrieval_handler():
    import retrieval.handler as rh
    importlib.reload(rh)
    return rh


# Collection → Retrieval: Events
class TestCollectionToRetrievalEvents:
    def test_pipeline_written_data_is_readable_by_retrieval(
        self, aws_resources
    ):
        """Collection writes → Retrieval can find the events."""
        run_pipeline(area="New South Wales", house_price=950000)
        rh = get_retrieval_handler()

        response = rh.lambda_handler(
            build_event("GET /api/v1/events",
                        {"suburb": "N/A", "state": "New South Wales"}),
            None
        )

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert len(body["events"]) >= 1

    def test_pipeline_written_price_is_correct(self, aws_resources):
        """Price stored by Collection matches what Retrieval returns."""
        run_pipeline(area="New South Wales", house_price=950000,
                     dwelling_price=None)
        rh = get_retrieval_handler()

        response = rh.lambda_handler(
            build_event("GET /api/v1/events",
                        {"suburb": "N/A", "state": "New South Wales"}),
            None
        )
        body = json.loads(response["body"])

        prices = [e["attributes"]["price"] for e in body["events"]]
        assert 950000.0 in prices

    def test_pipeline_written_event_has_correct_structure(self, aws_resources):
        """Events returned by Retrieval have all required response fields."""
        run_pipeline(area="Victoria", house_price=800000, dwelling_price=None)
        rh = get_retrieval_handler()

        response = rh.lambda_handler(
            build_event("GET /api/v1/events",
                        {"suburb": "N/A", "state": "Victoria"}),
            None
        )
        body = json.loads(response["body"])
        evt = body["events"][0]

        assert "eventId" in evt
        assert "eventType" in evt
        assert "timeObject" in evt
        assert "timestamp" in evt["timeObject"]
        assert "locations" in evt
        assert "attributes" in evt
        assert "price" in evt["attributes"]
        assert "state" in evt["attributes"]
        assert "suburb" in evt["attributes"]

    def test_pipeline_location_key_matches_retrieval_query(self, aws_resources):
        """Collection uses STATE#N/A format — Retrieval query must match."""
        run_pipeline(area="Queensland", house_price=700000, dwelling_price=None)
        rh = get_retrieval_handler()

        # Querying with state="Queensland", suburb="N/A" should hit the key
        response = rh.lambda_handler(
            build_event("GET /api/v1/events",
                        {"suburb": "N/A", "state": "Queensland"}),
            None
        )
        body = json.loads(response["body"])

        assert response["statusCode"] == 200
        assert len(body["events"]) >= 1
        assert body["events"][0]["attributes"]["suburb"] == "N/A"
        assert body["events"][0]["attributes"]["state"] == "Queensland"

    def test_null_prices_not_written_by_pipeline(self, aws_resources):
        """Collection skips null prices — Retrieval should return empty."""
        run_pipeline(area="Tasmania", house_price=None, dwelling_price=None)
        rh = get_retrieval_handler()

        response = rh.lambda_handler(
            build_event("GET /api/v1/events",
                        {"suburb": "N/A", "state": "Tasmania"}),
            None
        )
        body = json.loads(response["body"])

        assert response["statusCode"] == 200
        assert body["events"] == []

    def test_missing_suburb_returns_400_regardless_of_pipeline_data(
        self, aws_resources
    ):
        """Retrieval always returns 400 when suburb is missing."""
        run_pipeline()
        rh = get_retrieval_handler()

        response = rh.lambda_handler(
            build_event("GET /api/v1/events", {"state": "New South Wales"}),
            None
        )

        assert response["statusCode"] == 400


# Collection → Retrieval: Recent Events
class TestCollectionToRetrievalRecentEvents:
    def test_recent_endpoint_reads_pipeline_written_data(self, aws_resources):
        """Collection writes events → recent endpoint returns them."""
        run_pipeline(area="New South Wales", house_price=950000)
        rh = get_retrieval_handler()

        response = rh.lambda_handler(
            build_event("GET /api/v1/events/recent",
                        {"suburb": "N/A", "state": "New South Wales"}),
            None
        )

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert "events" in body
        assert len(body["events"]) >= 1

    def test_recent_endpoint_missing_state_returns_400(self, aws_resources):
        """Validation still returns 400 even when real pipeline data exists."""
        run_pipeline()
        rh = get_retrieval_handler()

        response = rh.lambda_handler(
            build_event("GET /api/v1/events/recent", {"suburb": "N/A"}),
            None
        )

        assert response["statusCode"] == 400

    def test_recent_endpoint_returns_at_most_10_pipeline_events(
        self, aws_resources
    ):
        """Recent endpoint returns at most 10 events even with more in DB."""
        for i in range(12):
            run_pipeline(
                area="New South Wales",
                date=f"2024-{i + 1:02d}-01",
                house_price=900000 + i * 1000,
                dwelling_price=None
            )
        rh = get_retrieval_handler()

        response = rh.lambda_handler(
            build_event("GET /api/v1/events/recent",
                        {"suburb": "N/A", "state": "New South Wales"}),
            None
        )
        body = json.loads(response["body"])

        assert response["statusCode"] == 200
        assert len(body["events"]) <= 10


# Collection → Retrieval: Datasets
class TestCollectionToRetrievalDatasets:
    def test_pipeline_written_dataset_is_readable_by_retrieval(
        self, aws_resources
    ):
        """Collection writes dataset metadata → Retrieval returns it."""
        run_pipeline()
        rh = get_retrieval_handler()

        response = rh.lambda_handler(
            build_event("GET /api/v1/datasets"),
            None
        )

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert "DataSets" in body
        assert len(body["DataSets"]) == 1

    def test_pipeline_dataset_contains_correct_fields(self, aws_resources):
        """Dataset written by Collection has the fields Retrieval exposes."""
        run_pipeline()
        rh = get_retrieval_handler()

        response = rh.lambda_handler(
            build_event("GET /api/v1/datasets"),
            None
        )
        body = json.loads(response["body"])
        ds = body["DataSets"][0]

        assert "datasetId" in ds
        assert "name" in ds
        assert ds["name"] == "ABS Total Value of Dwellings"
        assert "datasource" in ds
        assert ds["datasource"] == "www.abs.gov.au"
