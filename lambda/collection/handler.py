import json
import os
from collection.pipelines import *
from collection.spiders.www_abs_gov_au.total_value_of_dwellings import *
from collection.spiders.nswpropertysalesdata_com.property_sales_information import *

def lambda_handler(event, context):
    bucket = os.environ.get("BUCKET_NAME")

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
            spider.start()

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
