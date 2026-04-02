import json
import logging
import os
from collection.pipelines import (
        TotalValueOfDwellingsPipeline,
        PropertySalesNswPipeline
)
from collection.spiders.www_abs_gov_au.total_value_of_dwellings import (
    TotalValueOfDwellingsSpider
)
from collection.spiders.nswpropertysalesdata_com.property_sales_information import (
    PropertySalesNswSpider
)

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    bucket = os.environ.get("BUCKET_NAME")
    logger.info(json.dumps({"event": "collection_started", "bucket": bucket}))

    spiders = []

    absSpider = TotalValueOfDwellingsSpider()
    absPipeline = TotalValueOfDwellingsPipeline(
        absSpider.getName(), absSpider.getDomain(), bucket)
    absSpider.setPipeline(absPipeline)
    spiders.append(absSpider)

    propertySalesNswSpider = PropertySalesInformationSpider()
    propertySalesNswPipeline = PropertySalesInformationPipeline(
        propertySalesNswSpider.getName(), propertySalesNswSpider.getDomain(), bucket)
    propertySalesNswSpider.setPipeline(propertySalesNswPipeline)
    spiders.append(propertySalesNswSpider)
    
    try:
        for spider in spiders:
            logger.info(json.dumps(
                {"event": "spider_started", "spider": spider.getName()}))
            spider.start()
            logger.info(json.dumps(
                {"event": "spider_finished", "spider": spider.getName()}))

    except Exception as e:
        logger.error(json.dumps(
            {"event": "collection_error", "error": str(e)}))
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'message': f'Internal Error: {str(e)}'})
        }
    else:
        logger.info(json.dumps(
            {"event": "collection_success", "spiders_run": len(spiders)}))
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'message': 'Scraper Successful!'})
        }


if __name__ == "__main__":
    lambda_handler({}, None)
