# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html

# useful for handling different item types with a single interface
from itemadapter import ItemAdapter
from datetime import datetime
import os
import json
import boto3

class DatasetPipeline:
    def __init__(self, crawlerName, crawlerDomain):
        self.timestamp = datetime.now().isoformat()
        self.events = []
        self.crawlerName = crawlerName
        self.crawlerDomain = crawlerDomain

    @classmethod
    def from_crawler(cls, crawler):
        crawlerName = getattr(crawler.spidercls, 'name', crawler.spidercls.name)
        crawlerDomain = getattr(crawler.spidercls, 'domain', crawler.spidercls.name)
        return cls(crawlerName, crawlerDomain)

    def process_item(self, item):
        self.events.append(item)
        return item

    def close_spider(self):
        data = {
            "datasets": [{
                "data_source": self.crawlerDomain,
                "data_set_type": self.crawlerName,
                "timestamp": self.timestamp,
                "events": self.events
            }]
        }

        path = f"scraped/{self.crawlerDomain}/{self.crawlerName}_{self.timestamp}.json"
        # os.makedirs(os.path.dirname(path), exist_ok=True)
        # self.file = open(path, "w")
        # json.dump(data, self.file, indent=2)
