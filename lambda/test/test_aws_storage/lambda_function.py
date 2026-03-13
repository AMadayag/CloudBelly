import os
import json
import uuid
import boto3
from decimal import Decimal
from datetime import datetime, timezone
from botocore.exceptions import ClientError

AWS_REGION = "us-east-1"
S3_BUCKET_NAME = "cloudbelly-dev-raw-events"
DDB_TABLE_NAME = "cloudbelly-dev-housing-events"

s3 = boto3.client("s3", region_name=AWS_REGION)
dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
table = dynamodb.Table(DDB_TABLE_NAME)

def lambda_handler(event, context):
    now = datetime.now(timezone.utc).isoformat()
    test_id = str(uuid.uuid4())

    # Build a fake housing event

    raw_event = {
        "eventId": test_id,
        "state": "NSW",
        "suburb": "Newtown",
        "date": "2026-03-12",
        "price": 1250000,
        "address": "12 Example St",
        "propertyType": "house",
        "ingestedAt": now
    }

    # Upload raw JSON to S3

    s3_key = f"test/{test_id}.json"

    try:
        s3.put_object(
            Bucket=S3_BUCKET_NAME,
            Key=s3_key,
            Body=json.dumps(raw_event).encode("utf-8"),
            ContentType="application/json",
        )
        print(f"[OK] Uploaded test object to S3: s3://{S3_BUCKET_NAME}/{s3_key}")
    except ClientError as e:
        raise ClientError(f"[FAIL] S3 put_object failed - {e}")

    # Read it back from S3

    try:
        s3_response = s3.get_object(Bucket=S3_BUCKET_NAME, Key=s3_key)
        s3_body = s3_response["Body"].read().decode("utf-8")
        print("[OK] Read object back from S3")
        print("S3 contents:", s3_body)
    except ClientError as e:
        raise ClientError(f"[FAIL] S3 get_object failed - {e}")

    # Write structured item to DynamoDB

    item = {
        "location": "NSW#Newtown",
        "date": "2026-03-12",
        "eventId": test_id,
        "price": Decimal("1250000"),
        "address": "12 Example St",
        "propertyType": "house",
        "state": "NSW",
        "suburb": "Newtown",
        "sourceFileKey": s3_key,
        "ingestedAt": now,
    }

    try:
        table.put_item(Item=item)
        print("[OK] Wrote test item to DynamoDB")
    except ClientError as e:
        raise ClientError(f"[FAIL] DynamoDB put_item failed - {e}")

    # Read it back from DynamoDB

    try:
        response = table.get_item(
            Key={
                "location": "NSW#Newtown",
                "date": "2026-03-12",
            }
        )
        print("[OK] Read item back from DynamoDB")
        print("DynamoDB item:", json.dumps(response.get("Item", {}), default=str, indent=2))
    except ClientError as e:
        raise ClientError(f"[FAIL] DynamoDB get_item failed - {e}")
    return {
        'statusCode': 200,
        'body': json.dumps('[OK] All tests passed!')
    }
