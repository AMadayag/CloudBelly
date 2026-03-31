import json
import logging
import os
from datetime import datetime, timezone

import requests

logger = logging.getLogger()
logger.setLevel(logging.INFO)

BASE_URL = os.environ.get(
    "API_BASE_URL", "https://tvfiek3hzi.execute-api.us-east-1.amazonaws.com/dev")


def make_test(name, fn):
    """Run a single test function and return a result dict."""
    try:
        fn()
        logger.info(json.dumps({"event": "test_passed", "test": name}))
        return {"name": name, "status": "PASS", "error": None}
    except AssertionError as e:
        logger.warning(json.dumps({"event": "test_failed", "test": name, "error": str(e)}))
        return {"name": name, "status": "FAIL", "error": str(e)}
    except Exception as e:
        logger.error(json.dumps({"event": "test_error", "test": name, "error": str(e)}))
        return {"name": name, "status": "ERROR", "error": str(e)}


def get(path, params=None):
    """Make a GET request to the API and return the response."""
    url = f"{BASE_URL}{path}"
    response = requests.get(url, params=params, timeout=10)
    return response


def test_events_returns_200():
    r = get("/api/v1/events", params={"suburb": "N/A", "state": "Sydney"})
    assert r.status_code == 200, f"Expected 200, got {r.status_code}"


def test_events_returns_events_key():
    r = get("/api/v1/events", params={"suburb": "N/A", "state": "Sydney"})
    body = r.json()
    assert "events" in body, f"Response missing 'events' key: {body}"


def test_events_missing_suburb_returns_400():
    r = get("/api/v1/events")
    assert r.status_code == 400, f"Expected 400 when suburb missing, got {r.status_code}"


def test_events_with_date_filter():
    r = get("/api/v1/events", params={
        "suburb": "N/A",
        "state": "Sydney",
        "startDate": "2020-01-01",
        "endDate": "2024-12-31"
    })
    assert r.status_code == 200, f"Expected 200 with date filter, got {r.status_code}"


def test_datasets_returns_200():
    r = get("/api/v1/datasets")
    assert r.status_code == 200, f"Expected 200, got {r.status_code}"


def test_datasets_returns_datasets_key():
    r = get("/api/v1/datasets")
    body = r.json()
    assert "DataSets" in body, f"Response missing 'DataSets' key: {body}"


def test_summary_returns_200():
    r = get("/api/v1/analytics/summary", params={"suburb": "N/A", "state": "Sydney"})
    assert r.status_code == 200, f"Expected 200, got {r.status_code}"


def test_summary_missing_suburb_returns_400():
    r = get("/api/v1/analytics/summary")
    assert r.status_code == 400, f"Expected 400 when suburb missing, got {r.status_code}"


def test_summary_response_shape():
    r = get("/api/v1/analytics/summary", params={"suburb": "N/A", "state": "Sydney"})
    body = r.json()
    assert "labels" in body, f"Response missing 'labels': {body}"
    assert "datasets" in body, f"Response missing 'datasets': {body}"


def test_price_trend_returns_200():
    r = get("/api/v1/analytics/price-trend", params={"suburb": "N/A", "state": "Sydney"})
    assert r.status_code == 200, f"Expected 200, got {r.status_code}"


def test_price_trend_missing_suburb_returns_400():
    r = get("/api/v1/analytics/price-trend")
    assert r.status_code == 400, f"Expected 400 when suburb missing, got {r.status_code}"


def test_price_trend_response_shape():
    r = get("/api/v1/analytics/price-trend", params={"suburb": "N/A", "state": "Sydney"})
    body = r.json()
    assert "labels" in body, f"Response missing 'labels': {body}"
    assert "datasets" in body, f"Response missing 'datasets': {body}"


ALL_TESTS = [
    # Events
    ("GET /events returns 200",               test_events_returns_200),
    ("GET /events returns events key",         test_events_returns_events_key),
    ("GET /events missing suburb returns 400", test_events_missing_suburb_returns_400),
    ("GET /events with date filter",           test_events_with_date_filter),

    # Datasets
    ("GET /datasets returns 200",              test_datasets_returns_200),
    ("GET /datasets returns datasets key",     test_datasets_returns_datasets_key),

    # Summary
    ("GET /analytics/summary returns 200",              test_summary_returns_200),
    ("GET /analytics/summary missing suburb 400",       test_summary_missing_suburb_returns_400),
    ("GET /analytics/summary response shape",           test_summary_response_shape),

    # Price trend
    ("GET /analytics/price-trend returns 200",          test_price_trend_returns_200),
    ("GET /analytics/price-trend missing suburb 400",   test_price_trend_missing_suburb_returns_400),
    ("GET /analytics/price-trend response shape",       test_price_trend_response_shape),
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
        "summary": {
            "total": total,
            "passed": passed,
            "failed": failed,
            "errored": errored,
        },
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
