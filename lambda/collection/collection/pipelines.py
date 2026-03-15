# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
from itemadapter import ItemAdapter
import json
from datetime import datetime
import os

class SuburbJsonPipeline:
    def __init__(self):
        self.events = []
        self.timestamp = datetime.now().isoformat()

    def process_item(self, item):
        self.events.append(item)
        return item

    def open_spider(self):
        path = f"scraped/www_onthehouse_com_au/suburb-research_{self.timestamp}.json"
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self.file = open(path, "w")

    def close_spider(self):
        data = {
            "datasets": [{
                "data_source": "https://www.onthehouse.com.au/suburb-research",
                "data_set_type": "Suburb Summary",
                "timestamp": self.timestamp,
                "events": self.events
            }]
        }

        json.dump(data, self.file, indent=4)

class HousingJsonPipeline:
    def __init__(self, domain):
        self.events = []
        self.timestamp = datetime.now().isoformat()
        self.domain = domain

    @classmethod
    def from_crawler(cls, crawler):
        domain = getattr(crawler.spidercls, 'domain', crawler.spidercls.name)
        return cls(domain)

    def process_item(self, item):
        self.events.append(item)
        return item

    def open_spider(self):
        path = f"scraped/{self.domain}/house-listings_{self.timestamp}.json"
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self.file = open(path, "w")

    def close_spider(self):
        data = {
            "datasets": [{
                "data_source": f"https://{self.domain}",
                "data_set_type": "House Listings",
                "timestamp": self.timestamp,
                "events": self.events
            }]
        }

        json.dump(data, self.file)
