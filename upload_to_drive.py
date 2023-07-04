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
from concurrent.futures import ThreadPoolExecutor


# Set up Flask app
upload_blueprint = Blueprint('upload', __name__)
upload_blueprint.secret_key = '@unblinded2018'
executor = ThreadPoolExecutor()


# Google OAuth 2.0 configuration
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
    redirect_uri='urn:ietf:wg:oauth:2.0:oob'  # Use a placeholder redirect URI
)


# Redirect user to Google for authentication
@upload_blueprint.route('/')
def index():
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true'
    )
    # Replace the redirect_uri placeholder with the actual URL
    authorization_url = authorization_url.replace('urn:ietf:wg:oauth:2.0:oob', 'https://flask-production-d5a3.up.railway.app/upload_callback')
    return redirect(authorization_url)

# Callback route after authentication
@upload_blueprint.route('/upload_callback')
def upload_callback():
    # Fetch the authorization code from the callback request
    access_token = session.get('zoom_access_token')
    recordings = download_zoom_recordings(access_token)
    
    authorization_code = request.args.get('code')
    print(recordings)
    # Exchange the authorization code for a token
    flow.fetch_token(authorization_response=request.url)


    # Create a Google Drive service instance using the credentials
    credentials = flow.credentials
    drive_service = build('drive', API_VERSION, credentials=credentials)


    # Start a background task for uploading videos
    executor.submit(upload_videos, recordings, drive_service)


    return 'Video upload process started!'

def upload_videos(recordings, drive_service):
    folder_ids = {}  # Dictionary to store topic names and their corresponding folder IDs
    
    for recording in recordings:
        topic_name = recording.get('topic')
        folder_name = topic_name.replace(' ', '_')  # Replace spaces with underscores to create folder name

        if folder_name in folder_ids:
            folder_id = folder_ids[folder_name]
        else:
            # Check if the folder already exists in Google Drive
            folder_query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder'"
            existing_folders = drive_service.files().list(q=folder_query, fields='files(id)').execute()

            if existing_folders.get('files'):
                folder_id = existing_folders['files'][0]['id']
                folder_ids[folder_name] = folder_id
            else:
                # Create the folder in Google Drive
                folder_metadata = {
                    'name': folder_name,
                    'mimeType': 'application/vnd.google-apps.folder'
                }
                folder = drive_service.files().create(body=folder_metadata, fields='id').execute()
                folder_id = folder['id']
                folder_ids[folder_name] = folder_id

        for files in recording['recording_files']:
            # Check if the status is "completed" and the file extension is "mp4"
            if files['status'] == 'completed' and files['file_extension'] == 'MP4':
                # Fetch the video file from the download URL
                download_url = files['download_url']
                response = requests.get(download_url)
                video_content = response.content

                # Upload the video to the existing or newly created folder in Google Drive
                file_name = topic_name + '.mp4'
                file_metadata = {
                    'name': file_name,
                    'parents': [folder_id]
                }
                media = MediaIoBaseUpload(io.BytesIO(video_content), mimetype='video/mp4')
                drive_service.files().create(
                    body=file_metadata,
                    media_body=media,
                    fields='id'
                ).execute()

    print('Video upload completed!')
