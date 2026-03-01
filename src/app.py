import json
import boto3
import os

table_name = os.environ.get('TABLE_NAME')
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(table_name)

def lambda_handler(event, context):
    def lambda_handler(event, context):
    # API Gateway gives us the unique ID for this specific user session
        connection_id = event.get('requestContext', {}).get('connectionId')
    
    try:
        # Save the connection ID so we can send messages to it later
        table.put_item(Item={'connectionId': connection_id})
        print(f"Stored connectionId: {connection_id}")
        
        return {
            'statusCode': 200, 
            'body': json.dumps({'message': 'Connected.'})
        }
    except Exception as e:
        print(f"Error saving connection: {e}")
        return {
            'statusCode': 500, 
            'body': json.dumps({'message': 'Failed to connect.'})
        }
    