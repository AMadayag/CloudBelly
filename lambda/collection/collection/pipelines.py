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
from pathlib import Path

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
        s3Client.put_object(Bucket=self.bucket, Key=path, 
            Body=json.dumps(data).encode("utf-8"), ContentType="application/json")

class TotalValueOfDwellingsPipeline(DatasetPipeline):
    def finish(self):
        super().finish()
        dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
        table = dynamodb.Table(os.environ['TABLE_NAME'])

        datasets_table = dynamodb.Table(os.environ['DATASETS_TABLE_NAME'])
        datasets_table.put_item(Item={
            "datasetId": f"ds_{str(uuid.uuid4())}",
            "name": "ABS Total Value of Dwellings",
            "datasource": self.crawlerDomain,
            "locations": list(set([event['area'] for event in self.getEvents()])),
            "eventCount": len(self.getEvents())
        })
        
        for event in self.getEvents():
            table.put_item(Item={
                "eventId": str(uuid.uuid4()),
                "date": event.date,
                "state": event.area,
                "suburb": "N/A",
                "value": event.median_price_of_established_house_transfers,
                "propertyType": "house",
            })
            table.put_item(Item={
                "eventId": str(uuid.uuid4()),
                "date": event.date,
                "state": event.area,
                "suburb": "N/A",
                "value": event.median_price_of_attached_dwelling_transfers,
                "propertyType": "attached_dwelling"
            })

class PropertySalesInformationPipeline(DatasetPipeline):
    def finish(self):
        super().finish()
        dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
        table = dynamodb.Table("cloudbelly-dev-housing-events")
        for event in self.getEvents():
            propertyType = "N/A"
            if event["Primary purpose"] == "Residence" \
            and event["Property unit number"] == "":
                propertyType = "house"
            elif event["Primary purpose"] == "Residence" \
            and event["Property unit number"] != "":
                propertyType = "unit"
            else:
                propertyType = event["Primary purpose"]

            table.put_item(Item={
                "eventId": str(uuid.uuid4()),
                "date": event["Settlement date"],
                "state": "NSW",
                "suburb": event["Property locality"],
                "value": event["Purchase price"],
                "propertyType": propertyType,
            })

