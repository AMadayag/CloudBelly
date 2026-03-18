# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html

# useful for handling different item types with a single interface
from datetime import datetime
import os
import json
import boto3

class DatasetPipeline:
    def __init__(self, name, domain, bucket):
        self.timestamp = datetime.now().isoformat()
        self.events = []
        self.crawlerName = name
        self.crawlerDomain = domain
        self.bucket = bucket

    def processItem(self, item):
        self.events.append(item)

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
        client = boto3.client('s3')
        response = client.put_object(Bucket=self.bucket, Key=path, 
            Body=json.dumps(data).encode("utf-8"))
        # file = open(path, "w")
        # json.dump(data, file, indent=2)
