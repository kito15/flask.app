import os
import requests
import io
import tempfile
from datetime import datetime
from flask import Flask, redirect, request, Blueprint, current_app, session
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from download import download_zoom_recordings
from celery import Celery

# Set up Flask app
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
flow = Flow.from_client_secrets_file(
    CLIENT_SECRETS_FILE,
    scopes=SCOPES,
    redirect_uri='https://flask-production-d5a3.up.railway.app/upload_callback'  # Replace with your domain
)

# Create a Celery app
app = Flask(__name__)
app.config['CELERY_BROKER_URL'] = os.environ.get('REDIS_URL')
app.config['CELERY_RESULT_BACKEND'] = os.environ.get('REDIS_URL')
celery = Celery(app.name, broker=app.config['CELERY_BROKER_URL'])
celery.conf.update(app.config)

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
    # Fetch the authorization code from the callback request
    access_token = session.get('zoom_access_token')
    recordings = download_zoom_recordings(access_token)
    authorization_code = request.args.get('code')

    # Exchange the authorization code for a token
    flow.fetch_token(authorization_response=request.url)

    # Create a Google Drive service instance using the credentials
    credentials = flow.credentials
    drive_service = build('drive', API_VERSION, credentials=credentials)

    # Process recordings in the background using Celery
    process_recordings.delay(recordings, drive_service)

    return 'Video upload task has started!'

@celery.task
def process_recordings(recordings, drive_service):
    for recording in recordings:
        for files in recording['recording_files']:
            # Check if the status is "completed" and the file extension is "mp4"
            if files['status'] == 'completed' and files['file_extension'] == 'MP4':
                # Fetch the video file from the download URL
                download_url = files['download_url']
                response = requests.get(download_url)
                video_content = response.content

                # Upload the video to Google Drive
                file_name = recording.get('topic') + '.mp4'
                file_metadata = {'name': file_name}
                media = MediaIoBaseUpload(io.BytesIO(video_content), mimetype='video/mp4')
                drive_service.files().create(
                    body=file_metadata,
                    media_body=media,
                    fields='id'
                ).execute()

    return 'Video upload completed!'

