import os

def lambda_handler(event, context):
    print(f"FULL EVENT FOR DEBUGGING: {event}")
    
    qsp = event.get('queryStringParameters', {})

    token = qsp.get('token') if qsp else event.get('token')

    effect = 'Allow' if token else 'Deny'
   
    method_arn = event['methodArn']
    arn_parts = method_arn.split(':')
    api_gateway_parts = arn_parts[5].split('/')
    
    resource = f"arn:aws:execute-api:{arn_parts[3]}:{arn_parts[4]}:{api_gateway_parts[0]}/{api_gateway_parts[1]}/*"

    print(f"Decision: {effect} for Token: {token[:10]}...") 
    
    return {
        "principalId": "user",
        "policyDocument": {
            "Version": "2012-10-10",
            "Statement": [
                {
                    "Action": "execute-api:Invoke",
                    "Effect": effect,
                    "Resource": resource
                }
            ]
        }
    }