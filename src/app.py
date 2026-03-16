import os
import boto3
import time

TABLE_NAME = os.environ.get('TABLE_NAME')
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(TABLE_NAME)


def lambda_handler(event, context):
    request_context = event.get('requestContext', {})
    connection_id = request_context.get('connectionId')

    if not connection_id:
        print("ERROR: No connectionId in event")
        return {'statusCode': 400, 'body': 'Bad request.'}

    authorizer = request_context.get('authorizer', {})
    user_id = authorizer.get('userId', 'unknown')
    email = authorizer.get('email', '')
    ttl = int(time.time()) + (24 * 60 * 60)  # expire after 24h

    try:
        table.put_item(Item={
            'connectionId': connection_id,
            'userId': user_id,
            'email': email,
            'connectedAt': int(time.time()),
            'ttl': ttl
        })
        print(f"Connected: {connection_id} | user: {user_id} ({email})")
        return {'statusCode': 200, 'body': 'Connected.'}

    except Exception as e:
        print(f"Error saving connection {connection_id}: {e}")
        return {'statusCode': 500, 'body': 'Failed to connect.'}
    

    #This file handles "DId you connect yet ?"