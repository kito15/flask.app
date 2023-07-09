from flask import Flask, redirect, request, Blueprint
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from download import download_zoom_recordings
from tasks import uploadFiles
import pickle
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
    redirect_uri='https://flask-production-d5a3.up.railway.app/upload_callback'  # Replace with your domain
)

# Redirect user to Google for authentication
@upload_blueprint.route('/')
def index():
    # Check if the access token is already stored in Redis
    access_token = redis_client.get('google_access_token')
    if access_token:
        # Create credentials from the stored access token
        credentials = pickle.loads(access_token)
        # Check if the credentials are expired and refresh if needed
        if credentials.expired and credentials.refresh_token:
            access_token = credentials.refresh(Request())
            redis_client.set('google_access_token', access_token)
    else:
        # If access token is not available, initiate the authentication flow
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

# Callback route after authentication
@upload_blueprint.route('/upload_callback')
def upload_callback():
    authorization_code = request.args.get('code')
    flow.fetch_token(authorization_response=request.url)

    # Create a Google Drive service instance using the credentials
    credentials = flow.credentials

    # Store the access token in Redis
    access_token = pickle.dumps(credentials)
    redis_client.set('google_access_token', access_token)

    recordings = download_zoom_recordings()

    params = retrieve_parameters()
    accountName = params[0] if len(params) > 0 else None
    email = params[1] if len(params) > 1 else None
    
    serialized_credentials = pickle.dumps(credentials)
    
    uploadFiles.delay(serialized_credentials, recordings, accountName, email)
    
    return "Recordings are being uploaded"
