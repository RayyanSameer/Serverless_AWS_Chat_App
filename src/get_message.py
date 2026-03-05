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
    all_messages = []
    response = msg_table.scan()
    
    while True:
        all_messages.extend(response.get('Items', []))
        
        if 'LastEvaluatedKey' not in response:
            break
        
        response = msg_table.scan(
            ExclusiveStartKey=response['LastEvaluatedKey']
        )
    
    all_messages.sort(key=lambda x: x['timestamp'])
    return {'statusCode': 200, 'body': json.dumps(all_messages)}