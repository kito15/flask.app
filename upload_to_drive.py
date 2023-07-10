from flask import Flask, redirect, request, Blueprint
from google_auth_oauthlib.flow import Flow
from download import download_zoom_recordings
from tasks import uploadFiles
import pickle
import os
import redis

upload_blueprint = Blueprint('upload', __name__)
upload_blueprint.secret_key = '@unblinded2018'

os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
stored_params = []

# Redis configuration
REDIS_URL = 'redis://default:2qCxa3AEmJTH61oG4oa8@containers-us-west-90.railway.app:7759'
redis_client = redis.Redis.from_url(REDIS_URL)

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
    
def store_parameters(accountName, email):
    global stored_params
    stored_params = [accountName, email]
    
def retrieve_parameters():
    global stored_params
    return stored_params
    
# Callback route after authentication
@upload_blueprint.route('/upload_callback')
def upload_callback():
    authorization_code = request.args.get('code')
    flow.fetch_token(authorization_response=request.url)

    # Retrieve access token from Redis
    access_token = redis_client.get('google_access_token')

    if access_token:
        # Set the access token in the credentials object
        credentials = flow.credentials
        credentials.token = access_token.decode('utf-8')

        # Create a Google Drive service instance using the credentials
        recordings = download_zoom_recordings()

        params = retrieve_parameters()
        accountName = params[0] if len(params) > 0 else None
        email = params[1] if len(params) > 1 else None

        serialized_credentials = pickle.dumps(credentials)

        uploadFiles.delay(serialized_credentials, recordings, accountName, email)

        return "Recordings are being uploaded"
    else:
        # Store the access token in Redis
        credentials = flow.credentials
        access_token = credentials.token

        redis_client.set('google_access_token', access_token)

        return "Access token stored in Redis. You can now log in from any device."
