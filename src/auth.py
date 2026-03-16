

import os
import json
import urllib.request
from jose import jwk, jwt


_jwks_cache = None #Module Level var :) 


REGION = os.environ['AWS_REGION']
USER_POOL_ID = os.environ['USER_POOL_ID']
APP_CLIENT_ID = os.environ['APP_CLIENT_ID']
JWKS_URL = f"https://cognito-idp.{REGION}.amazonaws.com/{USER_POOL_ID}/.well-known/jwks.json"

#This is the meat of the authentication logic 
# it starts by caching the jwk as a global varaiable 
# Then performs a validation of said JWT through Key and Key ID validation

#When someone tries to connect to the chat, they hand over a JWT token. This file checks if that token is real and valid. If yes  Allow. If no — Deny. That's it.


def get_jwks():
    global _jwks_cache
    if _jwks_cache == None:
        with urllib.request.urlopen     (JWKS_URL) as response:
            jwk =  json.loads(response.read())
            _jwks_cache= jwk
            return _jwks_cache
    else:
        return _jwks_cache    



def verify_token(token):
    try:
        jwks = get_jwks()
        headers = jwt.get_unverified_headers(token)
        kid = headers['kid']
        key = next((k for k in jwks['keys'] if k['kid'] == kid), None)
        if not key:
            return None
        claims = jwt.decode(token, key, algorithms=['RS256'], audience=APP_CLIENT_ID)
        if claims.get('token_use') not in ('id', 'access'):
            return None
        return claims
    except Exception as e:
        print(f"Token verification failed: {e}")
        return None


def lambda_handler(event, context):
    print(f"Auth event received for route: {event.get('requestContext', {}).get('routeKey')}")

    method_arn = event.get('methodArn', '')
    qsp = event.get('queryStringParameters') or {}
    token = qsp.get('token') or event.get('token')

    claims = verify_token(token) if token else None
    effect = 'Allow' if claims else 'Deny'
    principal_id = claims.get('sub', 'unauthorized') if claims else 'unauthorized'

    try:
        arn_parts = method_arn.split(':')
        region = arn_parts[3]
        account = arn_parts[4]
        api_id = arn_parts[5].split('/')[0]
        stage = arn_parts[5].split('/')[1]
        resource = f"arn:aws:execute-api:{region}:{account}:{api_id}/{stage}/*"
    except Exception as e:
        print(f"ARN parsing error: {e}")
        resource = method_arn

    print(f"Decision: {effect} for principal: {principal_id}")

    return {
        "principalId": principal_id,
        "policyDocument": {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Action": "execute-api:Invoke",
                    "Effect": effect,
                    "Resource": resource
                }
            ]
        },
        "context": {
            "userId": principal_id,
            "email": claims.get('email', '') if claims else ''
        }
    }