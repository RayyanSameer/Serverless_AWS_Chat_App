import json
import time
import boto3
import os
from boto3.dynamodb.conditions import Key
from rate_limiter import check_rate_limit  # Token Bucket logic

# Initialize outside handler for speed
dynamodb = boto3.resource('dynamodb')
conn_table = dynamodb.Table(os.environ.get('TABLE_NAME'))

def lambda_handler(event, context):

    req_context = event.get('requestContext', {})
    connection_id = req_context.get('connectionId')
    

    authorizer = req_context.get('authorizer', {})
    user_id = authorizer.get('userId', connection_id)
    email = authorizer.get('email', 'Anonymous')


    if not check_rate_limit(user_id):
        return {'statusCode': 429, 'body': 'Too many messages!'}


    try:
        body = json.loads(event.get('body', '{}'))
        message = body.get('message', '')
    except Exception:
        return {'statusCode': 400, 'body': 'Invalid JSON format'}

    if not message:
        return {'statusCode': 200} # Nothing to broadcast

    
    gateway = boto3.client(
        'apigatewaymanagementapi',
        endpoint_url=f"https://{req_context['domainName']}/{req_context['stage']}"
    )

    online_users = []
    query_params = {
        'IndexName': 'StatusIndex',
        'KeyConditionExpression': Key('status').eq('online'),
        'ProjectionExpression': 'connectionId'
    }

    while True:
        response = conn_table.query(**query_params)
        online_users.extend(response.get('Items', []))
        if 'LastEvaluatedKey' not in response:
            break
        query_params['ExclusiveStartKey'] = response['LastEvaluatedKey']

   
    payload = json.dumps({
        'sender': email,
        'message': message,
        'timestamp': int(time.time())
    })

    stale_ids = []
    for user in online_users:
        target_id = user['connectionId']
        try:
            gateway.post_to_connection(ConnectionId=target_id, Data=payload)
        except gateway.exceptions.GoneException:
      
            stale_ids.append(target_id)
        except Exception as e:
            print(f"Failed to send to {target_id}: {e}")


    if stale_ids:
        with conn_table.batch_writer() as batch:
            for sid in stale_ids:
                batch.delete_item(Key={'connectionId': sid})

    return {'statusCode': 200, 'body': 'Sent.'}