from pathlib import Path
import scrapy
from scrapy.selector import Selector
import re
import os
from datetime import datetime

class HousingDataSpider(scrapy.spiders.SitemapSpider):
    name = "housing-data"
    domain = "www.oldlistings.com.au"
    webDirectory = os.path.basename(os.path.dirname(__file__))
    custom_settings = {
        "ITEM_PIPELINES": {"collection.pipelines.HousingJsonPipeline": 300},
        "LOG_LEVEL": "INFO"
    }
    sitemap_urls = ["https://www.oldlistings.com.au/sitemap.xml"]
    sitemap_rules = [('buy(/\d*)?$', 'parse')]

    def parse(self, response):
        listings = response.xpath('//div[contains(@class, "property bg-light")]')

        for listing in listings:
            attributes = {}

            attributes["source_url"] = response.url

            if name := listing.xpath('//div[1]/div[1]/h2/text()').get():
                attributes["name"] = name
            if numBed := listing.xpath('//div[1]/div[1]/ul/li[strong[text()="Bed:"]]/text()').get():
                attributes["num_bed"] = numBed
            if numBath := listing.xpath('//div[1]/div[1]/ul/li[strong[text()="Bath:"]]/text()').get():
                attributes["num_bath"] = numBath
            if numCar := listing.xpath('//div[1]/div[1]/ul/li[strong[text()="Car:"]]/text()').get():
                attributes["num_car"] = numCar
            if land := listing.xpath('//div[1]/div[1]/ul/li[strong[text()="Land:"]]/text()').get():
                attributes["land"] = land
            if category := listing.xpath('//div[1]/div[1]/ul/li[strong[text()="Category:"]]/text()').get():
                attributes["category"] = category
            if lastAdvertised := listing.xpath('//div[1]/div[2]/small/text()').get().split(': ')[1]:
                attributes["last_advertised"] = lastAdvertised
            if finalTransactionStatus := listing.xpath('//div[1]/div[2]/h3/text()').get():
                attributes["final_transaction_status"] = finalTransactionStatus

            status = listing.xpath('//div[2]/ul/li/text()').getall()
            dates = listing.xpath('//div[2]/ul/li/small/text()').getall()
            historicalData = [{"date": d, "status": s} for d, s in zip(dates, status)]
            attributes["historical_data"] = historicalData

            yield attributes

