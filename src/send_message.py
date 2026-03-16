import json
import time
import boto3
import os
from boto3.dynamodb.conditions import Key

dynamodb = boto3.resource('dynamodb')
conn_table = dynamodb.Table(os.environ['CONNECTIONS_TABLE'])

def lambda_handler(event, context):
    # Parse incoming WebSocket message
    body = json.loads(event.get('body', '{}'))
    message = body.get('message', '')

    # Extract caller identity
    request_context = event.get('requestContext', {})
    user_id = request_context.get('connectionId')
    authorizer = request_context.get('authorizer', {})
    email = authorizer.get('email')

    # Build API Gateway Management client
    domain = request_context['domainName']
    stage = request_context['stage']
    gateway = boto3.client(
        'apigatewaymanagementapi',
        endpoint_url=f'https://{domain}/{stage}'
    )

    # Paginated scan  collect ALL active connection IDs
    all_connections = []
    response = conn_table.scan(ProjectionExpression='connectionId')

    while True:
        all_connections.extend(response.get('Items', []))
        if 'LastEvaluatedKey' not in response:
            break
        response = conn_table.scan(
            ProjectionExpression='connectionId',
            ExclusiveStartKey=response['LastEvaluatedKey']
        )

    # Build broadcast payload
    payload = json.dumps({
        'sender': email or user_id,
        'message': message,
        'timestamp': int(time.time())
    })

    # Broadcast to all connections, track stale ones
    stale = []
    for conn in all_connections:
        target_id = conn['connectionId']
        try:
            gateway.post_to_connection(ConnectionId=target_id, Data=payload)
        except gateway.exceptions.GoneException:
            stale.append(target_id)
        except Exception as e:
            print(f"Failed to send to {target_id}: {e}")

    # Clean up disconnected clients
    for stale_id in stale:
        conn_table.delete_item(Key={'connectionId': stale_id})
        print(f"Cleaned stale connection: {stale_id}")

    print(f"Message from {user_id} | sent to {len(all_connections)} | cleaned {len(stale)} stale")
    return {'statusCode': 200, 'body': 'Message sent.'}