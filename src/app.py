import json
import boto3
import os

TABLE_NAME = os.environ.get('TABLE_NAME')
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(TABLE_NAME)

def lambda_handler(event, context):
   
    connection_id = event.get('requestContext', {}).get('connectionId')
    
    try:
  
        table.put_item(Item={'connectionId': connection_id})
        print(f"Stored connectionId: {connection_id}")
        
        return {
            'statusCode': 200, 
            'body': 'Connected.'
        }
    except Exception as e:
    
        print(f"Error saving connection: {e}")
        return {
            'statusCode': 500, 
            'body': 'Failed to connect.'
        }