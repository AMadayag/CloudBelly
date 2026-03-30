import requests
from lxml import html
import io
import zipfile
import csv

from collection.pipelines import DatasetPipeline
from collection.spiders.spider import Spider

class PropertySalesInformationSpider(Spider):
    def __init__(self):
        super().__init__("property_sales_information", "nswpropertysalesdata.com")

    def start(self):
        self.log("started")
        url = "https://nswpropertysalesdata.com/"
        self.parse(requests.get(url))
        self.pipeline.finish()
        self.log("Finished")

    def parse(self, response):
        self.log("parsing")
        htmlContent = html.fromstring(response.content)
        identifier1 = "download"
        identifier2 = "Download"
        dataCsvFile = htmlContent.xpath(f'//div[@id="{identifier1}" and a[text()="{identifier2}"]]/a/@href')[0]

        dataCsvLink = f"https://{self.getDomain()}{dataCsvFile}"
        self.log(f"Downloading: {dataCsvLink}")
        
        self.parseCsvData(requests.get(dataCsvLink))
    
    def parseCsvData(self, response):
        self.log("parsing CSV")
        with zipfile.ZipFile(io.BytesIO(response.content), "r") as file:
            csvFileName = file.namelist()[0]
            csvContents = file.read(csvFileName)
            reader = csv.DictReader(io.StringIO(csvContents.decode("utf-8")))
            for row in reader:
                self.pipeline.processItem(row)
