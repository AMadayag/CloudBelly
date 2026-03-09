import json
#just placeholder code so terraform can actually deploy

def lambda_handler(event, context):
    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps({'message': 'placeholder'})
    }