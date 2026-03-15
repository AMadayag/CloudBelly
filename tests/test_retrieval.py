import sys
import os

sys.path.append(os.path.abspath("lambda/collection"))

from handler import lambda_handler


def test_collection_handler_runs():
    response = lambda_handler({}, None)
    assert response is not None