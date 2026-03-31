import io
import re
import requests
import pandas as pd
from lxml import html
from collection.spiders.spider import Spider


class TotalValueOfDwellingsScraper(Spider):
    def __init__(self):
        super().__init__("total_value_of_dwellings", "www.abs.gov.au")

    def start(self):
        self.log("started")
        url = ("https://www.abs.gov.au/statistics/economy/"
               "price-indexes-and-inflation")
        url += "/total-value-dwellings/latest-release"
        self.parse(requests.get(url))
        self.log("Finished")

    def parse(self, response):
        self.log("parsing")
        html_content = html.fromstring(response.content)
        identifier = ("Median price and number of transfers "
                      "(capital city and rest of state)")
        data_xlsx_file = html_content.xpath(
            f'//div[div/div/h3[contains(text(),"{identifier}")]]//a/@href'
        )[0]

        data_xlsx_link = f"https://{self.getDomain()}{data_xlsx_file}"
        self.log(data_xlsx_link)

        self.parse_data_sheet(requests.get(data_xlsx_link))

    def parse_data_sheet(self, response):
        self.log("parsing data sheet")
        data = pd.read_excel(
            io.BytesIO(response.content),
            sheet_name="Data1",
            header=None,
            parse_dates=[0],
            date_format="%d-%m-%Y"
        ).replace({float('nan'): None}).T.values.tolist()

        dates = [x.split(' ')[0] for x in data[0][10:]]

        median_house = {}
        for col in [x for x in data[1:] if
                    re.match(r"Median Price of Established House Transfers",
                             x[0])]:
            area = col[0].split(';')[-2].strip()
            median_house[area] = [int(x * 1000) if x else x for x in col[10:]]

        median_dwell = {}
        for col in [x for x in data[1:] if
                    re.match(r"Median Price of Attached Dwelling Transfers",
                             x[0])]:
            area = col[0].split(';')[-2].strip()
            median_dwell[area] = [int(x * 1000) if x else x for x in col[10:]]

        num_house = {}
        for col in [x for x in data[1:] if
                    re.match(r"Number of Established House Transfers", x[0])]:
            area = col[0].split(';')[-2].strip()
            num_house[area] = col[10:]

        num_dwell = {}
        for col in [x for x in data[1:] if
                    re.match(r"Number of Attached Dwelling Transfers", x[0])]:
            area = col[0].split(';')[-2].strip()
            num_dwell[area] = col[10:]

        for area in num_house.keys():
            for x in zip(
                dates,
                median_house[area],
                num_house[area],
                median_dwell[area],
                num_dwell[area]
            ):
                self.pipeline.processItem({
                    "date": x[0],
                    "area": area,
                    "median_price_of_established_house_transfers": x[1],
                    "number_of_established_house_transfers": x[2],
                    "median_price_of_attached_dwelling_transfers": x[3],
                    "number_of_attached_dwelling_transfers": x[4],
                })
