import requests
import pandas as pd
from lxml import html
import io
import re
from collection.pipelines import DatasetPipeline
from collection.spiders.spider import Spider


class TotalValueOfDwellingsScraper(Spider):
    def __init__(self):
        super().__init__("total_value_of_dwellings", "www.abs.gov.au")

    def start(self):
        self.log("started")
        url = "https://www.abs.gov.au/statistics/economy/price-indexes-and-inflation/total-value-dwellings/latest-release"
        self.parse(requests.get(url))
        self.log("Finished")

    def parse(self, response):
        self.log("parsing")
        htmlContent = html.fromstring(response.content)
        identifier = "Median price and number of transfers (capital city and rest of state)"
        dataXlsxFile = htmlContent.xpath(
            f'//div[div/div/h3[contains(text(),"{identifier}")]]//a/@href')[0]

        dataXlsxLink = f"https://{self.getDomain()}{dataXlsxFile}"
        self.log(dataXlsxLink)

        self.parseDataSheet(requests.get(dataXlsxLink))

    def parseDataSheet(self, response):
        self.log("parsing data sheet")
        data = pd.read_excel(io.BytesIO(response.content), "Data1",
                             header=None,
                             parse_dates=[0],
                             date_format="%d-$m-$Y"
                             ).replace({float('nan'): None}).T.values.tolist()

        dates = [x.split(' ')[0] for x in data[0][10:]]

        medianPriceHouseTransfers = {}
        for col in [x for x in data[1:] if
                    re.match(r"Median Price of Established House Transfers", x[0])]:
            area = col[0].split(';')[-2].strip()
            medianPriceHouseTransfers[area] = [int(x * 1000) if x else x for x in col[10:]]

        medianPriceDwellTransfers = {}
        for col in [x for x in data[1:] if
                    re.match(r"Median Price of Attached Dwelling Transfers", x[0])]:
            area = col[0].split(';')[-2].strip()
            medianPriceDwellTransfers[area] = [int(x * 1000) if x else x for x in col[10:]]

        numHouseTransfers = {}
        for col in [x for x in data[1:] if
                    re.match(r"Number of Established House Transfers", x[0])]:
            area = col[0].split(';')[-2].strip()
            numHouseTransfers[area] = col[10:]

        numDwellTransfers = {}
        for col in [x for x in data[1:] if
                    re.match(r"Number of Attached Dwelling Transfers", x[0])]:
            area = col[0].split(';')[-2].strip()
            numDwellTransfers[area] = col[10:]

        for area in numHouseTransfers.keys():
            for x in zip(
                    dates,
                    medianPriceHouseTransfers[area],
                    numHouseTransfers[area],
                    medianPriceDwellTransfers[area],
                    numDwellTransfers[area]):
                self.pipeline.processItem({
                    "date": x[0],
                    "area": area,
                    "median_price_of_established_house_transfers": x[1],
                    "number_of_established_house_transfers": x[2],
                    "median_price_of_attached_dwelling_transfers": x[3],
                    "number_of_attached_dwelling_transfers": x[4],
                })
