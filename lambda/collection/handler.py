import json
import os
from collection.pipelines import DatasetPipeline
from collection.spiders.www_abs_gov_au.total_value_of_dwellings import TotalValueOfDwellingsScraper

def lambda_handler(event, context):
    bucket = os.environ.get("BUCKET_NAME")
    # settings.set("FEEDS", {f"s3://{bucket}/scraped/%(name)s_%(time)s.json": {"format": "json", "indent": 2}})
    # settings.set("FEEDS", {f"test.json": {"format": "json", "indent": 2}})

    spiders = [
        TotalValueOfDwellingsScraper()
    ]

    pipelines = []
    for spider in spiders:
        pipeline = DatasetPipeline(spider.getName(), spider.getDomain(), bucket)
        spider.setPipeline(pipeline)
        pipelines.append(pipeline)

    try:
        for x in spiders:
            x.start()

        for pipeline in pipelines:
            pipeline.finish()

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
    lambda_handler({}, None)
