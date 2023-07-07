import requests
import io
import os
import tempfile
from flask import Flask, redirect, request, Blueprint, current_app, session
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from download import download_zoom_recordings
import urllib.parse

upload_blueprint = Blueprint('upload', __name__)
upload_blueprint.secret_key = '@unblinded2018'

# Google OAuth 2.0 configuration
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
CLIENT_SECRETS_FILE = 'client_secrets.json'
SCOPES = [
    'https://www.googleapis.com/auth/drive.file',
    'https://www.googleapis.com/auth/drive',
    'openid',
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile'
]
API_VERSION = 'v3'

# Create the Flow instance
stored_params = []

flow = Flow.from_client_secrets_file(
    CLIENT_SECRETS_FILE,
    scopes=SCOPES,
    redirect_uri='https://flask-production-d5a3.up.railway.app/upload_callback'  # Replace with your domain
)

# Redirect user to Google for authentication
@upload_blueprint.route('/')
def index():
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true'
    )
    return redirect(authorization_url)
    
def share_folder_with_email(drive_service, folder_id, email):
    permission = {
        'type': 'user',
        'role': 'writer',
        'emailAddress': email
    }
    try:
        drive_service.permissions().create(fileId=folder_id, body=permission).execute()
        print(f"Folder shared with email: {email}")
    except errors.HttpError as e:
        print(f"Error sharing folder with email: {email}. Error: {str(e)}")     
    
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

    # Exchange the authorization code for a token
    flow.fetch_token(authorization_response=request.url)

    # Create a Google Drive service instance using the credentials
    credentials = flow.credentials
    drive_service = build('drive', API_VERSION, credentials=credentials)

    access_token = session.get('zoom_access_token')
    recordings = download_zoom_recordings(access_token)

    params=retrieve_parameters()
    accountName=params[0]
    email=params[1]
    
    uploadFiles(drive_service,recordings,accountName,email)
    
    return "Recording are being uploaded"
