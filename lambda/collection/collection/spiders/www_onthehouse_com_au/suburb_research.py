from pathlib import Path
import scrapy
from scrapy.selector import Selector
import re
import os
from datetime import datetime

class SuburbResearch(scrapy.Spider):
    name = "suburb-research"
    webDirectory = os.path.basename(os.path.dirname(__file__))
    custom_settings = {"ITEM_PIPELINES": {"collection.pipelines.SuburbJsonPipeline": 300}}
    async def start(self):
        urls = [
            f"https://www.onthehouse.com.au/suburb-research"
        ]

        for url in urls:
            yield scrapy.Request(url=url, callback=self.parse)

    def parse(self, response):
        # filename = "suburb-research.html"
        # Path(f"testFiles/{filename}").write_bytes(response.body)
        # self.log(f"Saved file {filename}")

        links = response.xpath('//ul[contains(@class, "StateLinks")]/li/a/@href').getall()
        for link in links:
            self.log(f"Following link {link}")
            statePage = response.urljoin(link)
            yield scrapy.Request(url=statePage, callback=self.parseState)

    def parseState(self, response):
        # page = response.url.split("/")[-1]
        # m = re.match(r"(?P<state>\w+)(?:\?page=(?P<pageNumber>\d*))?", page)
        # if m is None:
        #     raise scrapy.exceptions.DropItem("Cannot parse url!")

        # state = m.group("state")
        # pageNumber = m.group("pageNumber")
        # if m.group('pageNumber') is None:
        #     pageNumber = 1

        # filename = f"suburb-research.{state}{pageNumber}.html"

        # Path(f"testFiles/{filename}").write_bytes(response.body)
        # self.log(f"Saved file {filename}")

        nextPageLink = response.xpath('//ul[contains(@class, "pagination")]/li[13]/a/@href').get()
        if nextPageLink is not None:
            self.log(f"Following link {nextPageLink}")
            nextPage = response.urljoin(nextPageLink)
            yield scrapy.Request(url=nextPage, callback=self.parseState)

        suburbLinks = response.xpath('//ul[contains(@class, "StateSuburbList")]/li/a/@href').getall()
        for link in suburbLinks:
            self.log(f"Following link {link}")
            suburbPage = response.urljoin(link)
            yield scrapy.Request(url=suburbPage, callback=self.parseSuburb)

    def extractAgeDetails(self, ageResponse):
        pass

    def parseSuburb(self, response):
        # url = response.url.split("/")
        # page = f"{url[-2]}.{url[-1]}"

        # filename = f"suburb-research.{page}"

        # Path(f"testFiles/{filename}").write_bytes(response.body)
        # self.log(f"Saved file {filename}")
        houses = response.xpath('//div[contains(@class, "SuburbInsight") and .//h6[contains(normalize-space(), "Trends for Houses")]]')
        units = response.xpath('//div[contains(@class, "SuburbInsight") and .//h6[contains(normalize-space(), "Trends for Units")]]')
        # neighbourhoodInsights
        # age

        # This occurs when the page is missing
        if None in [houses, units]:
            # raise scrapy.exceptions.DropItem("Cannot parse url!")
            return

        yield {
            "market_insights": {
                "houses": {
                    "median_value": houses.xpath('//div[span[contains(text(), "Median Value")]]/p/text()').get(),
                    "median_growth": houses.xpath('//div[span[contains(text(), "Median Growth")]]/p/text()').get(),
                    "median_rent": houses.xpath('//div[span[contains(text(), "Median Rent")]]/p/text()').get(),
                    "rental_yield": houses.xpath('//div[span[contains(text(), "Rental Yield")]]/p/text()').get()
                },
                "units": {
                    "median_value": units.xpath('//div[span[contains(text(), "Median Value")]]/p/text()').get(),
                    "median_growth": units.xpath('//div[span[contains(text(), "Median Growth")]]/p/text()').get(),
                    "median_rent": units.xpath('//div[span[contains(text(), "Median Rent")]]/p/text()').get(),
                    "rental_yield": units.xpath('//div[span[contains(text(), "Rental Yield")]]/p/text()').get()
                }
            },
            "neighbourhood_insights": {
                "population": response.xpath('//*[@id="root"]/div/div[2]/div/div[1]/div/div[4]/div[2]/div[2]/div/div[2]/div[1]/div[2]/p/text()').get()
                # "age": extractAgeDetails(response.xpath('://*[@id="root"]/div/div[2]/div/div[1]/div/div[4]/div[2]/div[2]/div/div[2]').get())
            }
        }
