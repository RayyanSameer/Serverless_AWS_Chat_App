import json
import boto3
import os
import time

# Initialize the resources
TABLE_NAME = os.environ.get('TABLE_NAME')
MESSAGES_TABLE = os.environ.get('MESSAGES_TABLE')

dynamodb = boto3.resource('dynamodb')
conn_table = dynamodb.Table(TABLE_NAME)
msg_table = dynamodb.Table(MESSAGES_TABLE)

def lambda_handler(event, context):
    try:
        body = json.loads(event.get('body', '{}'))
        message = body.get('message', '')
        sender_id = event['requestContext']['connectionId']

        msg_table.put_item(Item={
            'id': 'global',
            'timestamp': int(time.time()),
            'sender': sender_id,
            'message': message
        })

 
        connections = conn_table.scan(ProjectionExpression='connectionId').get('Items', [])


        domain = event['requestContext']['domainName']
        stage = event['requestContext']['stage']
        gatewayapi = boto3.client('apigatewaymanagementapi', endpoint_url=f'https://{domain}/{stage}')

 
        for conn in connections:
            target_id = conn['connectionId']
            try:
                gatewayapi.post_to_connection(
                    ConnectionId=target_id,
                    Data=json.dumps({
                        "sender": sender_id,
                        "message": message
                    })
                )
            except gatewayapi.exceptions.GoneException:
                # If a user disconnected without us knowing, clean up the DB
                conn_table.delete_item(Key={'connectionId': target_id})

        return {'statusCode': 200}

    except Exception as e:
        print(f"Error: {str(e)}")
        return {'statusCode': 500, 'body': str(e)}