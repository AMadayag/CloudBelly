import os
import sys
import pytest
from unittest.mock import patch, MagicMock
from botocore.exceptions import ClientError

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


# Parse items
class TestParseItem:
    def test_returns_item_if_flat_structure(self):
        from analytics.handler import parse_item

        item = {
            "date": "2024-01-01",
            "price": 100,
            "suburb": "Sydney",
            "state": "NSW"
        }

        result = parse_item(item)

        assert result == item

    def test_flattens_nested_structure(self):
        from analytics.handler import parse_item

        item = {
            "Attributes": {
                "price": 200,
                "suburb": "Melbourne",
                "state": "VIC"
            },
            "Time object": {
                "timestamp": "2024-02-01T00:00:00Z"
            }
        }

        result = parse_item(item)

        assert result["date"] == "2024-02-01"
        assert result["price"] == 200
        assert result["suburb"] == "Melbourne"
        assert result["state"] == "VIC"

    def test_handles_missing_timestamp(self):
        from analytics.handler import parse_item

        item = {
            "Attributes": {
                "price": 300,
                "suburb": "Brisbane",
                "state": "QLD"
            }
        }

        result = parse_item(item)

        assert result["date"] == ""
        assert result["price"] == 300

    def test_handles_missing_attributes(self):
        from analytics.handler import parse_item

        item = {}

        result = parse_item(item)

        assert result["price"] is None
        assert result["suburb"] is None
        assert result["state"] is None


# Get items
class TestGetItems:
    @patch("analytics.handler.table")
    @patch("analytics.handler.parse_item")
    def test_query_without_dates(self, mock_parse, mock_table):
        from analytics.handler import get_items

        mock_table.query.return_value = {
            "Items": [{"raw": "data"}]
        }
        mock_parse.return_value = {"parsed": True}

        result = get_items("NSW#Sydney", None, None)

        mock_table.query.assert_called_once()
        assert result["Items"] == [{"parsed": True}]

    @patch("analytics.handler.table")
    def test_query_with_start_and_end_date(self, mock_table):
        from analytics.handler import get_items

        mock_table.query.return_value = {"Items": []}

        get_items("NSW#Sydney", "2024-01-01", "2024-02-01")

        args, kwargs = mock_table.query.call_args

        expr = kwargs["KeyConditionExpression"]
        assert expr is not None # ensures expression built

    @patch("analytics.handler.table")
    def test_query_with_only_start_date(self, mock_table):
        from analytics.handler import get_items

        mock_table.query.return_value = {"Items": []}

        get_items("NSW#Sydney", "2024-01-01", None)

        assert mock_table.query.called

    @patch("analytics.handler.table")
    def test_query_with_only_end_date(self, mock_table):
        from analytics.handler import get_items

        mock_table.query.return_value = {"Items": []}

        get_items("NSW#Sydney", None, "2024-02-01")

        assert mock_table.query.called

    @patch("analytics.handler.table")
    def test_parses_all_items(self, mock_table):
        from analytics.handler import get_items

        mock_table.query.return_value = {
            "Items": [
                {
                    "Attributes": {
                        "price": 100,
                        "suburb": "Sydney",
                        "state": "NSW"
                    },
                    "Time object": {"timestamp": "2024-01-01T00:00:00Z"}
                }
            ]
        }

        result = get_items("NSW#Sydney", None, None)

        assert result["Items"][0]["date"] == "2024-01-01"

    @patch("analytics.handler.table")
    def test_raises_runtime_error_on_dynamodb_failure(self, mock_table):
        from analytics.handler import get_items

        mock_table.query.side_effect = ClientError(
            {"Error": {"Code": "500", "Message": "fail"}},
            "Query"
        )

        with pytest.raises(RuntimeError):
            get_items("NSW#Sydney", None, None)


# Edge cases
class TestEdgeCases:
    def test_parse_item_partial_data(self):
        from analytics.handler import parse_item

        item = {
            "Attributes": {
                "price": None,
                "suburb": "Sydney",
                "state": None
            },
            "Time object": {
                "timestamp": "2024-01-01T00:00:00Z"
            }
        }

        result = parse_item(item)

        assert result["price"] is None
        assert result["state"] is None
        assert result["suburb"] == "Sydney"

    @patch("analytics.handler.table")
    def test_get_items_empty_response(self, mock_table):
        from analytics.handler import get_items

        mock_table.query.return_value = {}

        result = get_items("NSW#Sydney", None, None)

        assert result["Items"] == []

    @patch("analytics.handler.table")
    def test_get_items_handles_missing_items_key(self, mock_table):
        from analytics.handler import get_items

        mock_table.query.return_value = {}

        result = get_items("NSW#Sydney", None, None)

        assert "Items" in result
        assert result["Items"] == []
