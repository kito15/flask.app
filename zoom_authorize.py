import os
from flask import Flask, request, redirect, Blueprint
import requests
import base64
import time
import redis

zoom_blueprint = Blueprint('zoom', __name__)
zoom_blueprint.secret_key = '@unblinded2018'
# Zoom OAuth Configuration
client_id = 'N_IGn4DWQfuuklf8NDQA'
client_secret = '5IhTwYBVhqmpDKhIF1PUzEqHd9OMtiHD'
redirect_uri = 'https://flask-production-d5a3.up.railway.app/authorize'

# Establish Redis connection
redis_url = 'redis://default:2qCxa3AEmJTH61oG4oa8@containers-us-west-90.railway.app:7759'
redis_conn = redis.from_url(redis_url)

# Function to refresh the access token
def refresh_access_token(refresh_token):
    global client_id, client_secret
    token_endpoint = "https://zoom.us/oauth/token"

    post_data = {
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token
    }

    headers = {
        'Authorization': 'Basic ' + base64.b64encode((client_id + ':' + client_secret).encode()).decode(),
        'Content-Type': 'application/x-www-form-urlencoded'
    }

    response = requests.post(token_endpoint, data=post_data, headers=headers)
    token_data = response.json()

    # Refreshed access token retrieved
    access_token = token_data['access_token']
    return access_token

@zoom_blueprint.route('/authorize')
def authorize():
    # Check if access token exists in Redis
    access_token = redis_conn.get('access_token')
    if access_token:
        # Access token found, use it for further API requests
        return "Success"

    # Step 1: Redirect user to Zoom authorization page
    if 'code' not in request.args:
        authorization_url = f"https://zoom.us/oauth/authorize?response_type=code&client_id={client_id}&redirect_uri={redirect_uri}"
        return redirect(authorization_url)

    # Step 2: Exchange authorization code for an access token
    authorization_code = request.args['code']

    token_endpoint = f"https://zoom.us/oauth/token?grant_type=authorization_code&code={authorization_code}&client_id={client_id}&client_secret={client_secret}&redirect_uri={redirect_uri}"

    response = requests.post(token_endpoint)
    token_data = response.json()

    # Access token retrieved
    access_token = token_data['access_token']
    refresh_token = token_data['refresh_token']
    token_expires_at = time.time() + token_data['expires_in']  # Calculate the timestamp when the token will expire

    # Check if the access token has expired
    if time.time() >= token_expires_at:
        access_token = refresh_access_token(refresh_token)
        # Update the refreshed access token for further API requests
        redis_conn.set('access_token', access_token)
        redis_conn.expire('access_token', token_data['expires_in'])
    else:
        redis_conn.set('access_token', access_token)

    return "Success"
