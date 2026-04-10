import boto3
import time 
from decimal import Decimal

#Init DynamoDB resource and table

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('RateLimits')

MAX_TOKENS = 5
REFILL_RATE = 1 # tokens per second

def check_rate_limit(user_id):
    current_time = Decimal(str((time.time())))
    #Get Current token count 

    response = table.get_item(Key={'userId': user_id})

    #If user is new or no record exists, initialize with max tokens

    if 'Item' not in response:
        table.put_item(Item={
            'userId': user_id,
            'tokens': MAX_TOKENS - 1,
            'lastRefill': current_time
        })
        return True
    
    #If user exists, calculate tokens to refill based on elapsed time

    item = response['Item']
    last_refill = item['lastRefill']
    tokens = item['tokens']
    elapsed = current_time - last_refill
    refill_amount = Decimal(elapsed) * Decimal(REFILL_RATE)
    new_tokens = min(tokens + refill_amount, MAX_TOKENS)

    if new_tokens < 1:
        return False
    
    #Update token count

    table.update_item(
        Key={'userId': user_id},
        UpdateExpression='SET tokens = :newTokens, lastRefill = :currentTime',
        ExpressionAttributeValues={':newTokens': new_tokens - 1, ':currentTime': current_time}
        
    )
    return True

