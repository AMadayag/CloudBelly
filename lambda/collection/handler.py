import json
import os
from scrapy.crawler import AsyncCrawlerProcess
from scrapy.utils.project import get_project_settings
from collection.spiders.www_abs_gov_au.total_value_of_dwellings import TotalValueOfDwellings

def lambda_handler(event, context):
    bucket = os.environ.get("BUCKET_NAME")

    settings = get_project_settings()
    settings.set("FEEDS", {f"s3://{bucket}/scraped/%(name)s_%(time)s.json": {"format": "json", "indent": 2}})
    # settings.set("FEEDS", {f"test.json": {"format": "json", "indent": 2}})

    process = AsyncCrawlerProcess(settings)

    spiders = [
        TotalValueOfDwellings
    ]

    for spider in spiders:
        process.crawl(spider)

    try:
        process.start()
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({f'message': 'Internal Error: {str(e)}'})
        }   
    else:
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'message': 'Scraper Successful!'})
        }

if __name__ == "__main__":
    lambda_handler({},None)
