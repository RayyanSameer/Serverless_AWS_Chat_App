import os
import boto3

TABLE_NAME = os.environ.get('TABLE_NAME')
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(TABLE_NAME)


def lambda_handler(event, context):
    connection_id = event.get('requestContext', {}).get('connectionId')

    if not connection_id:
        print("ERROR: No connectionId in event")
        return {'statusCode': 400, 'body': 'Bad request.'}

    try:
        response = table.get_item(Key={'connectionId': connection_id})
        item = response.get('Item', {})
        user_id = item.get('userId', 'unknown')

        table.delete_item(Key={'connectionId': connection_id})
        print(f"Disconnected: {connection_id} | user: {user_id}")

    except Exception as e:
        print(f"Error removing connection {connection_id}: {e}")


    return {'statusCode': 200, 'body': 'Disconnected.'}