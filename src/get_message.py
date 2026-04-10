import json
import boto3
import os
from boto3.dynamodb.conditions import Key


#Psudocode :
# 1. Setup the message table
# 2. Define a list for the message 
# 3. Get via Lambda the last evaluated key 
# 4. Sort by timestamp 


MESSAGES_TABLE = os.environ.get('MESSAGES_TABLE')
dynamodb = boto3.resource('dynamodb')
msg_table = dynamodb.Table(MESSAGES_TABLE)


def lambda_handler(event, context):
    user_id = event['requestContext']['authorizer']['userId']
    qsp = event.get('queryStringParameters') or {}
    last_key = qsp.get('lastKey')

    query_params = {
        'IndexName': 'UserIdIndex',
        'KeyConditionExpression': Key('userId').eq(user_id),
        'ScanIndexForward': False,  # newest first
        'Limit': 40
    }
    if last_key:
        query_params['ExclusiveStartKey'] = {'userId': user_id, 'messageId': last_key}

    response = msg_table.query(**query_params)
    messages = response.get('Items', [])
    next_key = response.get('LastEvaluatedKey', {}).get('messageId')

    return {
        'statusCode': 200,
        'body': json.dumps({'messages': messages, 'nextKey': next_key})
    }