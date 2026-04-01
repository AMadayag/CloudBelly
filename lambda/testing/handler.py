import json
import logging
import os
from datetime import datetime, timezone

import requests
import pytest

logger = logging.getLogger()
logger.setLevel(logging.INFO)

BASE_URL = os.environ.get(
    "API_BASE_URL",
    "https://tvfiek3hzi.execute-api.us-east-1.amazonaws.com/dev",
)


def make_test(name, fn):
    try:
        fn()
        logger.info(json.dumps({"event": "test_passed", "test": name}))
        return {"name": name, "status": "PASS", "error": None}
    except AssertionError as e:
        logger.warning(json.dumps(
            {"event": "test_failed", "test": name, "error": str(e)}
        ))
        return {"name": name, "status": "FAIL", "error": str(e)}
    except Exception as e:
        logger.error(json.dumps(
            {"event": "test_error", "test": name, "error": str(e)}
        ))
        return {"name": name, "status": "ERROR", "error": str(e)}


def get(path, params=None):
    url = f"{BASE_URL}{path}"
    response = requests.get(url, params=params, timeout=10)
    return response


def test_events_returns_200():
    r = get("/api/v1/events", params={"suburb": "N/A", "state": "Sydney"})
    assert r.status_code == 200, f"Expected 200, got {r.status_code}"


def test_events_missing_suburb_returns_400():
    r = get("/api/v1/events")
    assert r.status_code == 400, (
        f"Expected 400 when suburb missing, got {r.status_code}"
    )


def test_datasets_returns_200():
    r = get("/api/v1/datasets")
    assert r.status_code == 200, f"Expected 200, got {r.status_code}"


def test_summary_returns_200():
    r = get("/api/v1/analytics/summary",
            params={"suburb": "N/A", "state": "Sydney"})
    assert r.status_code == 200, f"Expected 200, got {r.status_code}"


def test_price_trend_returns_200():
    r = get("/api/v1/analytics/price-trend",
            params={"suburb": "N/A", "state": "Sydney"})
    assert r.status_code == 200, f"Expected 200, got {r.status_code}"


class TestEvents:
    def test_response_has_events_key(self):
        r = get("/api/v1/events", params={"suburb": "N/A", "state": "NSW"})
        body = r.json()
        assert "events" in body, f"Missing 'events' key: {body}"

    def test_events_are_list(self):
        r = get("/api/v1/events", params={"suburb": "N/A", "state": "NSW"})
        body = r.json()
        assert isinstance(body["events"], list), (
            f"'events' should be a list, got: {type(body['events'])}")

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
            pytest.skip("No events in DB to validate shape")
        event = events[0]
        assert "eventId" in event
        assert "timeObject" in event and "timestamp" in event["timeObject"]
        assert "attributes" in event and "price" in event["attributes"]


class TestDatasets:
    def test_datasets_are_list(self):
        r = get("/api/v1/datasets")
        body = r.json()
        assert "DataSets" in body
        assert isinstance(body["DataSets"], list)


class TestSummary:
    def test_response_shape(self):
        r = get("/api/v1/analytics/summary",
                params={"suburb": "N/A", "state": "NSW"})
        body = r.json()
        assert "labels" in body and isinstance(body["labels"], list)
        assert "datasets" in body and isinstance(body["datasets"], list)


class TestPriceTrend:
    def test_datasets_have_label_and_data(self):
        r = get("/api/v1/analytics/price-trend",
                params={"suburb": "N/A", "state": "NSW"})
        body = r.json()
        datasets = body.get("datasets", [])
        if not datasets:
            pytest.skip("No price trend data")
        for ds in datasets:
            assert "label" in ds
            assert "data" in ds and isinstance(ds["data"], list)


ALL_TESTS = [
    ("GET /events returns 200",
        test_events_returns_200),
    ("GET /events missing suburb returns 400",
        test_events_missing_suburb_returns_400),
    ("GET /datasets returns 200",
        test_datasets_returns_200),
    ("GET /analytics/summary returns 200",
        test_summary_returns_200),
    ("GET /analytics/price-trend returns 200",
        test_price_trend_returns_200),
    ("TestEvents.test_response_has_events_key",
        TestEvents().test_response_has_events_key),
    ("TestEvents.test_events_are_list",
        TestEvents().test_events_are_list),
    ("TestEvents.test_date_filter_respects_bounds",
        TestEvents().test_date_filter_respects_bounds),
    ("TestEvents.test_event_shape",
        TestEvents().test_event_shape),
    ("TestDatasets.test_datasets_are_list",
        TestDatasets().test_datasets_are_list),
    ("TestSummary.test_response_shape",
        TestSummary().test_response_shape),
    ("TestPriceTrend.test_datasets_have_label_and_data",
        TestPriceTrend().test_datasets_have_label_and_data),
]


def lambda_handler(event, context):
    logger.info(json.dumps({"event": "testing_started", "base_url": BASE_URL}))

    results = [make_test(name, fn) for name, fn in ALL_TESTS]

    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = sum(1 for r in results if r["status"] == "FAIL")
    errored = sum(1 for r in results if r["status"] == "ERROR")
    total = len(results)

    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "base_url": BASE_URL,
        "summary": {"total": total, "passed": passed,
                    "failed": failed, "errored": errored},
        "results": results,
    }

    logger.info(json.dumps({
        "event": "testing_complete",
        "passed": passed,
        "failed": failed,
        "errored": errored,
        "total": total,
    }))

    all_passed = failed == 0 and errored == 0

    return {
        "statusCode": 200 if all_passed else 500,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(report, indent=2),
    }