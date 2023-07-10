from flask import Flask, redirect, request, Blueprint
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from download import download_zoom_recordings
from tasks import uploadFiles
import pickle
import os

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
def create_flow():
    return Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        redirect_uri='https://flask-production-d5a3.up.railway.app/upload_callback'  # Replace with your domain
    )

# Redirect user to Google for authentication
@upload_blueprint.route('/')
def index():
    flow = create_flow()
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true'
    )
    return redirect(authorization_url) 

def is_token_expired(credentials):
    if not credentials or not credentials.valid:
        return True
    if credentials.expired and credentials.refresh_token:
        return credentials.expired
    return False

def store_parameters(accountName,email):
    global stored_params
    stored_params=[accountName,email]

def retrieve_parameters():
    global stored_params
    stored_params[0].credentials = flow.credentials
    return stored_params

# Callback route after authentication
@upload_blueprint.route('/upload_callback')
def upload_callback():
    authorization_code = request.args.get('code')
    flow = create_flow()
    flow.fetch_token(authorization_response=request.url)

    # Create a Google Drive service instance using the credentials
    credentials = flow.credentials

    if is_token_expired(credentials):
        if credentials.refresh_token:
            credentials.refresh(Request())
        else:
            return "Refresh token is missing. Please authenticate again."

    # Store the refreshed credentials
    stored_params[0].credentials = credentials

    recordings = download_zoom_recordings()

    return "Recordings are being uploaded"
