# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html

# useful for handling different item types with a single interface
from datetime import datetime
import uuid
import os
import json
import boto3
# from pathlib import Path

AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')


class DatasetPipeline:
    def __init__(self, name, domain, bucket):
        self.timestamp = datetime.now().isoformat()
        self.events = []
        self.spiderName = name
        self.spiderDomain = domain
        self.bucket = bucket

    def processItem(self, item):
        self.events.append(item)

    def getEvents(self):
        return self.events

    def log(self, message):
        print(f"[Pipeline:{self.spiderName}] LOG: {message}")

    def finish(self):
        data = {
            "dataset": {
                "data_source": self.spiderDomain,
                "data_set_type": self.spiderName,
                "timestamp": self.timestamp,
                "events": self.events
            }
        }

        path = f"scraped/{self.spiderDomain}/{self.spiderName}_{self.timestamp}.json"
        # Path(path).parent.mkdir(parents=True, exist_ok=True)
        # file = open(path, "w")
        # json.dump(data, file, indent=2)
        # self.log(f"Saved to {path}")
        s3Client = boto3.client("s3", region_name=AWS_REGION)
        s3Client.put_object(
            Bucket=self.bucket,
            Key=path,
            Body=json.dumps(data).encode("utf-8"),
            ContentType="application/json"
        )


class TotalValueOfDwellingsPipeline(DatasetPipeline):
    def finish(self):
        super().finish()
        dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
        table = dynamodb.Table(os.environ['TABLE_NAME'])

        datasetsTable = dynamodb.Table(os.environ['DATASETS_TABLE_NAME'])
        datasetsTable.put_item(Item={
            "datasetId": f"ds_{str(uuid.uuid4())}",
            "name": "ABS Total Value of Dwellings",
            "datasource": self.spiderDomain,
            "locations": list(set([event['area'] for event in self.getEvents()])),
            "eventCount": len(self.getEvents())
        })

        for event in self.getEvents():
            houseEventId = f"evt_{uuid.uuid4()}"
            dwellingEventId = f"evt_{uuid.uuid4()}"

            if event['median_price_of_established_house_transfers']:
                table.put_item(Item={
                    "location": f"{event['area']}#N/A",
                    "eventId": houseEventId,
                    "eventKey": f"{event['date']}#{houseEventId}",
                    "date": event['date'],
                    "state": event['area'],
                    "suburb": "N/A",
                    "price": event['median_price_of_established_house_transfers'],
                    "property": "house",
                })

            if event['median_price_of_attached_dwelling_transfers']:
                table.put_item(Item={
                    "location": f"{event['area']}#N/A",
                    "eventId": dwellingEventId,
                    "eventKey": f"{event['date']}#{dwellingEventId}",
                    "date": event['date'],
                    "state": event['area'],
                    "suburb": "N/A",
                    "price": event['median_price_of_attached_dwelling_transfers'],
                    "property": "attached_dwelling"
                })


class PropertySalesInformationPipeline(DatasetPipeline):
    def finish(self):
        super().finish()
        dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
        datasetsTable = dynamodb.Table(os.environ['DATASETS_TABLE_NAME'])
        datasetsTable.put_item(Item={
            "datasetId": f"ds_{str(uuid.uuid4())}",
            "name": "NSW Property Sales Data",
            "datasource": self.spiderDomain,
            "locations": list(set([event['Property locality'] for event in self.getEvents()])),
            "eventCount": len(self.getEvents())
        })

        table = dynamodb.Table(os.environ['TABLE_NAME'])
        for event in self.getEvents():
            propertyType = "N/A"
            if event["Primary purpose"] == "Residence" and event["Property unit number"] == "":
                propertyType = "house"
            elif event["Primary purpose"] == "Residence" and event["Property unit number"] != "":
                propertyType = "unit"
            else:
                propertyType = event["Primary purpose"]

            suburb = event["Property locality"]
            houseEventId = f"evt_{uuid.uuid4()}"

            table.put_item(Item={
                "location": f"NSW#{suburb}",
                "eventId": houseEventId,
                "eventKey": f"{event['Settlement date']}#{houseEventId}",
                "date": event["Settlement date"],
                "state": "NSW",
                "suburb": suburb,
                "price": event["Purchase price"],
                "property": propertyType,
            })
