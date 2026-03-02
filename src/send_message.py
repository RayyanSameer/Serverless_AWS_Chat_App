import json
import boto3
import os
import time
import uuid

TABLE_NAME = os.environ.get('TABLE_NAME')
MESSAGES_TABLE = os.environ.get('MESSAGES_TABLE')

dynamodb = boto3.resource('dynamodb')
conn_table = dynamodb.Table(TABLE_NAME)
msg_table = dynamodb.Table(MESSAGES_TABLE)


def lambda_handler(event, context):
    try:
        body = json.loads(event.get('body') or '{}')
        message = body.get('message', '').strip()

        if not message:
            return {'statusCode': 400, 'body': 'Message cannot be empty.'}

        request_context = event['requestContext']
        connection_id = request_context['connectionId']

        authorizer = request_context.get('authorizer', {})
        user_id = authorizer.get('userId', connection_id)
        email = authorizer.get('email', '')

        
        msg_table.put_item(Item={
            'id': str(uuid.uuid4()),
            'timestamp': int(time.time()),
            'userId': user_id,
            'email': email,
            'message': message
        })

        # Broadcast to all connections
        domain = request_context['domainName']
        stage = request_context['stage']
        gateway = boto3.client(
            'apigatewaymanagementapi',
            endpoint_url=f'https://{domain}/{stage}'
        )

        connections = conn_table.scan(
            ProjectionExpression='connectionId'
        ).get('Items', [])

        payload = json.dumps({
            'sender': email or user_id,
            'message': message,
            'timestamp': int(time.time())
        })

        stale = []
        for conn in connections:
            target_id = conn['connectionId']
            try:
                gateway.post_to_connection(ConnectionId=target_id, Data=payload)
            except gateway.exceptions.GoneException:
                stale.append(target_id)
            except Exception as e:
                print(f"Failed to send to {target_id}: {e}")

       
        for stale_id in stale:
            conn_table.delete_item(Key={'connectionId': stale_id})
            print(f"Cleaned stale connection: {stale_id}")

        print(f"Message from {user_id} | sent to {len(connections)} | cleaned {len(stale)} stale")
        return {'statusCode': 200, 'body': 'Message sent.'}

    except Exception as e:
        print(f"Error in send_message: {e}")
        return {'statusCode': 500, 'body': str(e)}