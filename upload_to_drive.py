from flask import Flask, redirect, request, Blueprint
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
import os
import redis

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

# Redis configuration
REDIS_URL = 'redis://default:2qCxa3AEmJTH61oG4oa8@containers-us-west-90.railway.app:7759'
redis_client = redis.from_url(REDIS_URL)

# Create the Flow instance
flow = Flow.from_client_secrets_file(
    CLIENT_SECRETS_FILE,
    scopes=SCOPES,
    redirect_uri='https://flask-production-d5a3.up.railway.app/upload_callback'
)


# Function to store credentials in Redis
def store_credentials(credentials):
    access_token = credentials.token
    refresh_token = credentials.refresh_token
    expires_at = credentials.expiry.timestamp()
    redis_client.set('google_access_token', access_token)
    redis_client.set('google_refresh_token', refresh_token)
    redis_client.set('expires_at', expires_at)


# Function to load credentials from Redis
def load_credentials():
    access_token = redis_client.get('google_access_token')
    refresh_token = redis_client.get('google_refresh_token')
    expires_at = redis_client.get('expires_at')
    if access_token and refresh_token and expires_at:
        credentials = Credentials(
            token=access_token,
            refresh_token=refresh_token,
            token_uri=flow.fetch_token_uri,
            client_id=flow.client_config['client_id'],
            client_secret=flow.client_config['client_secret']
        )
        credentials.expiry = datetime.fromtimestamp(float(expires_at))
        return credentials
    return None


# Redirect user to Google for authentication
@upload_blueprint.route('/')
def index():
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true'
    )
    return redirect(authorization_url)


# Callback route after authentication
@upload_blueprint.route('/upload_callback')
def upload_callback():
    authorization_code = request.args.get('code')
    flow.fetch_token(authorization_response=request.url)

    # Create a Google Drive service instance using the credentials
    credentials = flow.credentials
    store_credentials(credentials)

    recordings = download_zoom_recordings()

    return "Recordings are being uploaded"
