from flask import Flask, redirect, request, Blueprint
from google_auth_oauthlib.flow import Flow
from download import download_zoom_recordings
from tasks import uploadFiles
import pickle
import os
import redis
import json
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

@upload_blueprint.route('/')
def index():
    access_token = redis_client.get('google_access_token')
    if access_token:
        # Continue with the upload process
          recordings = [
            {
                "uuid": "+3Dg6nTrQf2shXzuYOdkmg==",
                "id": 83229382123,
                "account_id": "-QuLHtVKSkqxjQwWNX6Iiw",
                "host_id": "ab3pXrJgQ7eIhk1Gg5XO1w",
                "topic": "Coaching Session With Glen Wagstaff",
                "type": 3,
                "start_time": "2023-07-03T16:03:05Z",
                "timezone": "America/New_York",
                "host_email": "admin@unblindedmastery.com",
                "duration": 0,
                "total_size": 544607,
                "recording_count": 1,
                "share_url": "https://us02web.zoom.us/rec/share/kEVF_Zif4BGfbNJDD00lM5aFNGSYZWYp5M3MSFudACN96akvqDxBlr0PVGtqNgRE.FagJDrDWpg01uvBv",
                "recording_files": [
                    {
                        "id": "5d6bb1dc-51f0-4a6a-beb4-b6ed961c4507",
                        "meeting_id": "+3Dg6nTrQf2shXzuYOdkmg==",
                        "recording_start": "2023-07-03T16:03:05Z",
                        "recording_end": "2023-07-03T16:03:21Z",
                        "file_type": "MP4",
                        "file_extension": "MP4",
                        "file_size": 544607,
                        "play_url": "https://us02web.zoom.us/rec/play/nhPMCkNABuueo8BIgjS_cHs-CZpbKWuDABKfIcuHoui39FThC5bbbue74-LEu_51DOCG1AWqtbICc6AU.K8KWcd0woJPuVkrL",
                        "download_url": "https://us02web.zoom.us/rec/download/nhPMCkNABuueo8BIgjS_cHs-CZpbKWuDABKfIcuHoui39FThC5bbbue74-LEu_51DOCG1AWqtbICc6AU.K8KWcd0woJPuVkrL",
                        "status": "completed",
                        "recording_type": "active_speaker"
                    }
                ]
            }
        ]

        accountName = "Glen Wagstaff"
        email = "rai6@njit.edu"

        serialized_credentials = redis_client.get('credentials')
        uploadFiles.delay(serialized_credentials, recordings, accountName, email)

        return "Recordings are being uploaded"
    else:
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'
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
    refresh_token = credentials.refresh_token
    token_url = 'https://oauth2.googleapis.com/token'
    
    with open(CLIENT_SECRETS_FILE, 'r') as secrets_file:
        client_secrets = json.load(secrets_file)
    
    token_params = {
        'client_id': client_secrets['web']['client_id'],
        'client_secret': client_secrets['web']['client_secret'],
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token
    }
    
    response = requests.post(token_url, data=token_params)

    if response.status_code == 200:
        new_credentials = response.json()
        new_access_token = new_credentials['access_token']

        # Store the new access token in Redis
        redis_client.set('google_access_token', new_access_token)

        # Update the existing credentials with the new access token
        credentials.token = new_access_token

        recordings = download_zoom_recordings()
        params = retrieve_parameters()
        accountName = params[0] if len(params) > 0 else None
        email = params[1] if len(params) > 1 else None
        
        serialized_credentials = pickle.dumps(credentials)
        redis_client.set('credentials', serialized_credentials)

        uploadFiles.delay(serialized_credentials, recordings, accountName, email)
        
        return "Recordings are being uploaded"
    else:
        return "Failed to refresh access token"
