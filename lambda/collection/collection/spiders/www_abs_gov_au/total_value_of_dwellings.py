import scrapy
from scrapy.selector import Selector
import pandas as pd
import io
import re

class TotalValueOfDwellings(scrapy.Spider):
    name = "total_value_of_dwellings"
    domain = "www.abs.gov.au"
    custom_settings = {
        "ITEM_PIPELINES": {"collection.pipelines.DatasetPipeline": 300},
        "LOG_LEVEL": "INFO"
    }
    start_urls = ["https://www.abs.gov.au/statistics/economy/price-indexes-and-inflation/total-value-dwellings/latest-release"]

    def parse(self, response):
        identifier = "Median price and number of transfers (capital city and rest of state)"
        dataXlsxDownload = response.xpath(f'//div[div/div/h3[contains(text(),"{identifier}")]]//a/@href').get()

        yield scrapy.Request(url=response.urljoin(dataXlsxDownload), callback=self.parseDataSheet)

    def parseDataSheet(self, response):
        data = pd.read_excel(io.BytesIO(response.body), "Data1", 
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
        
        areaData = {}
        for area in numHouseTransfers.keys():
            areaData[area] = list(map(lambda x: {
                "date": x[0],
                "median_price_of_established_house_transfers": x[1],
                "number_of_established_house_transfers": x[2],
                "median_price_of_attached_dwelling_transfers": x[3],
                "number_of_attached_dwelling_transfers": x[4],
                }, list(zip(dates, 
                medianPriceHouseTransfers[area], 
                numHouseTransfers[area],
                medianPriceDwellTransfers[area], 
                numDwellTransfers[area]
            ))))

        yield areaData
