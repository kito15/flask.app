from flask import Flask, redirect, request, Blueprint
from google_auth_oauthlib.flow import Flow
from download import download_zoom_recordings
from tasks import uploadFiles
import pickle
from google.oauth2.credentials import Credentials
import os
import redis
import requests

upload_blueprint = Blueprint('upload', __name__)
upload_blueprint.secret_key = '@unblinded2018'

os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
stored_params = []

# Google OAuth 2.0 configuration
CLIENT_SECRETS_FILE = 'client_secrets.json'
SCOPES = [
    'https://www.googleapis.com/auth/drive.file',
    'https://www.googleapis.com/auth/drive',
    'openid',
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile'
]

# Create the Flow instance
flow = Flow.from_client_secrets_file(
    CLIENT_SECRETS_FILE,
    scopes=SCOPES,
    redirect_uri='https://flask-production-d5a3.up.railway.app/upload_callback'  # Replace with your domain
)

# Create a Redis client instance
redis_url = 'redis://default:2qCxa3AEmJTH61oG4oa8@containers-us-west-90.railway.app:7759'
redis_client = redis.from_url(redis_url)

# Redirect user to Google for authentication
@upload_blueprint.route('/')
def index():
    # Check if access token exists in Redis
    access_token = redis_client.get('google_access_token')

    if access_token:
        # Continue with the upload process
        recordings = download_zoom_recordings()

        params = retrieve_parameters()

        accountName = params[0] if len(params) > 0 else None
        email = params[1] if len(params) > 1 else None

        serialized_credentials = redis_client.get('credentials')

        uploadFiles.delay(serialized_credentials, recordings, accountName, email)

        return "Recordings are being uploaded"
    else:
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true'
        )
        return redirect(authorization_url)

def store_parameters(accountName, email):
    global stored_params
    stored_params = [accountName, email]

def retrieve_parameters():
    global stored_params
    return stored_params

@upload_blueprint.route('/upload_callback')
def upload_callback():
    authorization_code = request.args.get('code')
    flow.fetch_token(authorization_response=request.url)

    # Refresh the access token
    credentials = flow.credentials
    request_url = 'https://oauth2.googleapis.com/token'
    refresh_token = credentials.refresh_token
    token_params = {
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret
    }
    response = requests.post(request_url, data=token_params)
    print(response)
    if response.status_code == 200:
        new_credentials = Credentials.from_authorized_user_info(response.json())
        new_access_token = new_credentials.token
        # Store the new access token in Redis
        redis_client.set('google_access_token', new_access_token)
        # Update the existing credentials with the new credentials
        credentials.token = new_access_token
        serialized_credentials = pickle.dumps(credentials)
        redis_client.set('credentials', serialized_credentials)

        recordings = download_zoom_recordings()

        params = retrieve_parameters()

        accountName = params[0] if len(params) > 0 else None
        email = params[1] if len(params) > 1 else None

        uploadFiles.delay(serialized_credentials, recordings, accountName, email)

        return "Recordings are being uploaded"
    else:
        return "Failed to refresh access token"
