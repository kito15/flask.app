from flask import Flask, redirect, request, Blueprint
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from download import download_zoom_recordings
from tasks import uploadFiles
import pickle
import os
import redis

upload_blueprint = Blueprint('upload', __name__)
upload_blueprint.secret_key = '@unblinded2018'

os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
stored_params = []
redis_url = 'redis://default:2qCxa3AEmJTH61oG4oa8@containers-us-west-90.railway.app:7759'

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

# Create a Redis client
redis_client = redis.Redis.from_url(redis_url)

@upload_blueprint.route('/')
def index():
    tokens = retrieve_tokens()
    if tokens and not tokens.expired:
        # Access token is available and not expired, skip authentication
        return redirect('/upload_callback?code=' + tokens.authorization_code)

    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true'
    )
    return redirect(authorization_url)

def store_tokens(tokens):
    # Store the tokens in Redis
    serialized_tokens = pickle.dumps(tokens)
    redis_client.set('google_tokens', serialized_tokens)

def retrieve_tokens():
    # Retrieve the tokens from Redis
    serialized_tokens = redis_client.get('google_tokens')
    if serialized_tokens:
        return pickle.loads(serialized_tokens)
    return None

def refresh_tokens():
    # Retrieve the refresh token from Redis
    refresh_token = retrieve_tokens()['refresh_token']
    # Use the refresh token to obtain new access and refresh tokens
    flow.fetch_token(
        token_url='https://accounts.google.com/o/oauth2/token',
        client_id=flow.client_config['client_id'],
        client_secret=flow.client_config['client_secret'],
        refresh_token=refresh_token
    )
    # Update the stored tokens with the new tokens
    store_tokens(flow.credentials)

def get_credentials():
    tokens = retrieve_tokens()
    if not tokens or tokens.expired:
        refresh_tokens()
    return Credentials.from_authorized_user(tokens)
    
def store_parameters(accountName,email):
    global stored_params
    stored_params=[accountName,email]
    
def retrieve_parameters():
    global stored_params
    return stored_params

# Callback route after authentication
@upload_blueprint.route('/upload_callback')
def upload_callback():
    authorization_code = request.args.get('code')
    flow.fetch_token(authorization_response=request.url)

    # Create a Google Drive service instance using the credentials
    credentials = flow.credentials

    # Store the tokens
    store_tokens(credentials)

    recordings = download_zoom_recordings()

    params = retrieve_parameters()

    accountName = params[0] if len(params) > 0 else None
    email = params[1] if len(params) > 1 else None

    serialized_credentials = pickle.dumps(credentials)

    uploadFiles.delay(serialized_credentials, recordings, accountName, email)

    return "Recordings are being uploaded"
