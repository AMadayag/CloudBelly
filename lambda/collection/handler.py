import json
import os
from scrapy.crawler import AsyncCrawlerProcess
from scrapy.utils.project import get_project_settings
from collection.spiders.www_oldlistings_com_au.housing_data import HousingDataSpider

def lambda_handler(event, context):
    bucket = os.environ.get("BUCKET_NAME")
    # awsAccessKeyId = os.environ.get("BUCKET_NAME")
    # awsSecretAccessKey = os.environ.get("BUCKET_NAME")

    settings = get_project_settings()
    # settings.set("AWS_ACCESS_KEY_ID", awsAccessKeyId, 
    #     "AWS_SECRET_ACCESS_KEY", awsSecretAccessKey)

    process = AsyncCrawlerProcess(settings)

    spiders = [
       HousingDataSpider
    ]

    for spider in spiders:
        process.crawl(spider, bucketName=bucket)

    process.start()

    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps({'message': 'placeholder'})
    }

if __name__ == "__main__":
    lambda_handler({},None)
