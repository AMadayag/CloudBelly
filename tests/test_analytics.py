import sys
import os

sys.path.append(os.path.abspath("lambda/analytics"))

from handler import lambda_handler


def test_analytics_handler_runs():
    response = lambda_handler({}, None)
    assert response is not None