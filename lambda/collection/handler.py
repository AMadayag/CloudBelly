import json
import os
from collection.pipelines import TotalValueOfDwellingsPipeline
from collection.spiders.www_abs_gov_au.total_value_of_dwellings import (
    TotalValueOfDwellingsScraper,
)


def lambda_handler(event, context):
    bucket = os.environ.get("BUCKET_NAME")

    spiders = []
    pipelines = []

    abs_scraper = TotalValueOfDwellingsScraper()
    abs_pipeline = TotalValueOfDwellingsPipeline(
        abs_scraper.getName(), abs_scraper.getDomain(), bucket
    )
    abs_scraper.setPipeline(abs_pipeline)
    spiders.append(abs_scraper)
    pipelines.append(abs_pipeline)

    try:
        for spider in spiders:
            spider.start()

        for pipeline in pipelines:
            pipeline.finish()

    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'message': f'Internal Error: {str(e)}'})
        }
    else:
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'message': 'Scraper Successful!'})
        }


if __name__ == "__main__":
    lambda_handler({}, None)
