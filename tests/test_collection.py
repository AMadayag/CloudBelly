import sys
import os
import boto3
import pytest
from moto import mock_aws
from unittest.mock import patch, MagicMock

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
        "STAGE": "dev"
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

class TestDatasetPipeline:
    def test_process_item_appends_to_events(self, aws_resources):
        from collection.pipelines import DatasetPipeline
        pipeline = DatasetPipeline("test", "test.com", BUCKET_NAME)
        pipeline.processItem({"date": "2024-01-01", "area": "Sydney", "price": 500000})
        assert len(pipeline.getEvents()) == 1

    def test_get_events_returns_all_items(self, aws_resources):
        from collection.pipelines import DatasetPipeline
        pipeline = DatasetPipeline("test", "test.com", BUCKET_NAME)
        pipeline.processItem({"date": "2024-01-01", "area": "Sydney", "price": 500000})
        pipeline.processItem({"date": "2024-02-01", "area": "Brisbane", "price": 600000})
        assert len(pipeline.getEvents()) == 2


class TestTotalValueOfDwellingsPipeline:
    def test_finish_writes_to_dynamodb(self, aws_resources):
        from collection.pipelines import TotalValueOfDwellingsPipeline
        pipeline = TotalValueOfDwellingsPipeline("total_value_of_dwellings", "www.abs.gov.au", BUCKET_NAME)
        pipeline.processItem({
            "date": "2024-01-01",
            "area": "Sydney",
            "median_price_of_established_house_transfers": 950000,
            "median_price_of_attached_dwelling_transfers": 750000,
            "number_of_established_house_transfers": 100,
            "number_of_attached_dwelling_transfers": 50
        })
        pipeline.finish()

        table = aws_resources.Table(TABLE_NAME)
        result = table.scan()
        assert result["Count"] >= 1

    def test_finish_skips_null_prices(self, aws_resources):
        from collection.pipelines import TotalValueOfDwellingsPipeline
        pipeline = TotalValueOfDwellingsPipeline("total_value_of_dwellings", "www.abs.gov.au", BUCKET_NAME)
        pipeline.processItem({
            "date": "2024-01-01",
            "area": "Sydney",
            "median_price_of_established_house_transfers": None,
            "median_price_of_attached_dwelling_transfers": None,
            "number_of_established_house_transfers": None,
            "number_of_attached_dwelling_transfers": None
        })
        pipeline.finish()

        table = aws_resources.Table(TABLE_NAME)
        result = table.scan()
        assert result["Count"] == 0

    def test_finish_writes_dataset_metadata(self, aws_resources):
        from collection.pipelines import TotalValueOfDwellingsPipeline
        pipeline = TotalValueOfDwellingsPipeline("total_value_of_dwellings", "www.abs.gov.au", BUCKET_NAME)
        pipeline.processItem({
            "date": "2024-01-01",
            "area": "Sydney",
            "median_price_of_established_house_transfers": 950000,
            "median_price_of_attached_dwelling_transfers": 750000,
            "number_of_established_house_transfers": 100,
            "number_of_attached_dwelling_transfers": 50
        })
        pipeline.finish()

        datasets_table = aws_resources.Table(DATASETS_TABLE_NAME)
        result = datasets_table.scan()
        assert result["Count"] == 1
        assert result["Items"][0]["datasource"] == "www.abs.gov.au"

    def test_location_format(self, aws_resources):
        from collection.pipelines import TotalValueOfDwellingsPipeline
        pipeline = TotalValueOfDwellingsPipeline("total_value_of_dwellings", "www.abs.gov.au", BUCKET_NAME)
        pipeline.processItem({
            "date": "2024-01-01",
            "area": "Sydney",
            "median_price_of_established_house_transfers": 950000,
            "median_price_of_attached_dwelling_transfers": None,
            "number_of_established_house_transfers": 100,
            "number_of_attached_dwelling_transfers": None
        })
        pipeline.finish()

        table = aws_resources.Table(TABLE_NAME)
        result = table.scan()
        assert result["Items"][0]["location"] == "Sydney#N/A"


class TestLambdaHandler:
    def test_handler_returns_200_on_success(self, aws_resources):
        with patch("collection.spiders.www_abs_gov_au.total_value_of_dwellings.TotalValueOfDwellingsScraper") as MockScraper:
            mock_instance = MagicMock()
            MockScraper.return_value = mock_instance
            mock_instance.getName.return_value = "total_value_of_dwellings"
            mock_instance.getDomain.return_value = "www.abs.gov.au"
            mock_instance.start.return_value = None

            from handler import lambda_handler
            response = lambda_handler({}, None)
            assert response["statusCode"] == 200
