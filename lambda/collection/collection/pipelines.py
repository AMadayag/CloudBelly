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

AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')

class DatasetPipeline:
    def __init__(self, name, domain, bucket):
        self.timestamp = datetime.now().isoformat()
        self.events = []
        self.crawlerName = name
        self.crawlerDomain = domain
        self.bucket = bucket

    def processItem(self, item):
        self.events.append(item)

    def getEvents(self):
        return self.events

    def finish(self):
        data = {
            "dataset": {
                "data_source": self.crawlerDomain,
                "data_set_type": self.crawlerName,
                "timestamp": self.timestamp,
                "events": self.events
            }
        }

        path = f"scraped/{self.crawlerDomain}/{self.crawlerName}_{self.timestamp}.json"
        # file = open(path, "w")
        # json.dump(data, file, indent=2)
        s3Client = boto3.client("s3", region_name=AWS_REGION)
        s3Client.put_object(Bucket=self.bucket, Key=path, 
            Body=json.dumps(data).encode("utf-8"), ContentType="application/json")

class TotalValueOfDwellingsPipeline(DatasetPipeline):
    def finish(self):
        super().finish()
        dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
        table = dynamodb.Table(os.environ['TABLE_NAME'])
        for event in self.getEvents():
            table.put_item(Item={
                "location": f"{event['area']}#N/A",
                "eventKey": f"{event['date']}#{str(uuid.uuid4())}",
                "date": event['date'],
                "state": event['area'],
                "suburb": "N/A",
                "price": event['median_price_of_established_house_transfers'],
                "property": "house",
            })
            table.put_item(Item={
                "location": f"{event['area']}#N/A",
                "eventKey": f"{event['date']}#{str(uuid.uuid4())}",
                "date": event['date'],
                "state": event['area'],
                "suburb": "N/A",
                "price": event['median_price_of_attached_dwelling_transfers'],
                "property": "attached_dwelling"
            })
        
        datasets_table = dynamodb.Table(os.environ['DATASETS_TABLE_NAME'])
        datasets_table.put_item(Item={
            "datasetId": f"ds_{str(uuid.uuid4())}",
            "name": "ABS Total Value of Dwellings",
            "datasource": self.crawlerDomain,
            "locations": list(set([event['area'] for event in self.getEvents()])),
            "eventCount": len(self.getEvents())
        })
