# tests/test_e2e.py
import os
import requests
import pytest

BASE_URL = os.environ.get(
    "API_BASE_URL",
    "https://tvfiek3hzi.execute-api.us-east-1.amazonaws.com/dev",
)


def get(path, params=None):
    url = f"{BASE_URL}{path}"
    return requests.get(url, params=params, timeout=10)


# Events
class TestEvents:
    def test_returns_200(self):
        r = get("/api/v1/events", params={"suburb": "N/A", "state": "NSW"})
        assert r.status_code == 200, f"Expected 200, got {r.status_code}"

    def test_response_has_events_key(self):
        r = get("/api/v1/events", params={"suburb": "N/A", "state": "NSW"})
        body = r.json()
        assert "events" in body, f"Missing 'events' key: {body}"

    def test_events_are_list(self):
        r = get("/api/v1/events", params={"suburb": "N/A", "state": "NSW"})
        body = r.json()
        assert isinstance(body["events"], list), (
            f"'events' should be a list, got: {type(body['events'])}"
        )

    def test_missing_suburb_returns_400(self):
        r = get("/api/v1/events")
        assert r.status_code == 400, (
            f"Expected 400 when suburb missing, got {r.status_code}"
        )

    def test_date_filter_returns_200(self):
        r = get("/api/v1/events", params={
            "suburb": "N/A",
            "state": "NSW",
            "startDate": "2020-01-01",
            "endDate": "2024-12-31",
        })
        assert r.status_code == 200, (
            f"Expected 200 with date filter, got {r.status_code}"
        )

    def test_date_filter_respects_bounds(self):
        start = "2024-01-01"
        end = "2024-01-31"
        r = get("/api/v1/events", params={
            "suburb": "N/A",
            "state": "NSW",
            "startDate": start,
            "endDate": end,
        })
        assert r.status_code == 200
        body = r.json()
        for event in body["events"]:
            ts = event["timeObject"]["timestamp"][:10]
            assert start <= ts <= end, (
                f"Event timestamp {ts} outside [{start}, {end}]"
            )

    def test_event_shape(self):
        r = get("/api/v1/events", params={"suburb": "N/A", "state": "NSW"})
        body = r.json()
        events = body.get("events", [])
        if not events:
            pytest.skip("No events in DB to validate shape against")
        event = events[0]
        assert "eventId" in event, f"Missing 'eventId': {event}"
        assert "timeObject" in event, f"Missing 'timeObject': {event}"
        assert "timestamp" in event["timeObject"], (
            f"Missing 'timeObject.timestamp': {event}"
        )
        assert "attributes" in event, f"Missing 'attributes': {event}"
        assert "price" in event["attributes"], (
            f"Missing 'attributes.price': {event}"
        )


# Datasets
class TestDatasets:
    def test_returns_200(self):
        r = get("/api/v1/datasets")
        assert r.status_code == 200, f"Expected 200, got {r.status_code}"

    def test_response_has_datasets_key(self):
        r = get("/api/v1/datasets")
        body = r.json()
        assert "DataSets" in body, f"Missing 'DataSets' key: {body}"

    def test_datasets_are_list(self):
        r = get("/api/v1/datasets")
        body = r.json()
        assert isinstance(body["DataSets"], list), (
            f"'DataSets' should be a list, got: {type(body['DataSets'])}"
        )


# Analytics — Summary
class TestSummary:
    def test_returns_200(self):
        r = get("/api/v1/analytics/summary",
                params={"suburb": "N/A", "state": "NSW"})
        assert r.status_code == 200, f"Expected 200, got {r.status_code}"

    def test_missing_suburb_returns_400(self):
        r = get("/api/v1/analytics/summary")
        assert r.status_code == 400, (
            f"Expected 400 when suburb missing, got {r.status_code}"
        )

    def test_response_shape(self):
        r = get("/api/v1/analytics/summary",
                params={"suburb": "N/A", "state": "NSW"})
        body = r.json()
        assert "labels" in body, f"Missing 'labels': {body}"
        assert "datasets" in body, f"Missing 'datasets': {body}"
        assert isinstance(body["labels"], list), "'labels' should be a list"
        assert isinstance(body["datasets"], list), (
            "'datasets' should be a list"
        )

    def test_dataset_entries_have_expected_keys(self):
        r = get("/api/v1/analytics/summary",
                params={"suburb": "N/A", "state": "NSW"})
        body = r.json()
        datasets = body.get("datasets", [])
        if not datasets or not datasets[0].get("data"):
            pytest.skip("No summary data in DB to validate shape against")
        point = datasets[0]["data"][0]
        for key in ("min", "median", "max"):
            assert key in point, f"Summary data point missing '{key}': {point}"


# Analytics — Price Trend
class TestPriceTrend:
    def test_returns_200(self):
        r = get("/api/v1/analytics/price-trend",
                params={"suburb": "N/A", "state": "NSW"})
        assert r.status_code == 200, f"Expected 200, got {r.status_code}"

    def test_missing_suburb_returns_400(self):
        r = get("/api/v1/analytics/price-trend")
        assert r.status_code == 400, (
            f"Expected 400 when suburb missing, got {r.status_code}"
        )

    def test_response_shape(self):
        r = get("/api/v1/analytics/price-trend",
                params={"suburb": "N/A", "state": "NSW"})
        body = r.json()
        assert "labels" in body, f"Missing 'labels': {body}"
        assert "datasets" in body, f"Missing 'datasets': {body}"
        assert isinstance(body["datasets"], list), (
            "'datasets' should be a list"
        )

    def test_datasets_have_label_and_data(self):
        r = get("/api/v1/analytics/price-trend",
                params={"suburb": "N/A", "state": "NSW"})
        body = r.json()
        datasets = body.get("datasets", [])
        if not datasets:
            pytest.skip("No price trend data in DB to validate shape against")
        for ds in datasets:
            assert "label" in ds, f"Dataset missing 'label': {ds}"
            assert "data" in ds, f"Dataset missing 'data': {ds}"
            assert isinstance(ds["data"], list), (
                f"'data' should be a list: {ds}"
            )
