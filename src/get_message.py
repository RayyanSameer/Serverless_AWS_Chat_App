import json
import boto3
import os


#Psudocode :
# 1. Setup the message table
# 2. Define a list for the message 
# 3. Get via Lambda the last evaluated key 
# 4. Sort by timestamp 


MESSAGES_TABLE = os.environ.get('MESSAGES_TABLE')
dynamodb = boto3.resource('dynamodb')
msg_table = dynamodb.Table(MESSAGES_TABLE)

def lambda_handler(event, context):
    user_id = event['requestContext']['authorizer']['userId'] # Get the last evaluated key from the query parameters

    response = msg_table.query(
        IndexName="UserIdIndex",
        KeyConditionExpression=boto3.dynamodb.conditions.Key('userId').eq(user_id),
        ScanForward=False,
        Limit=40
    )

    messages = response.get('Items', [])
    return {
        'statusCode': 200,
        'body': json.dumps(messages)
    }