import requests
import io
import os
import tempfile
from datetime import datetime
from flask import Flask, redirect, request, Blueprint, current_app, session
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from download import download_zoom_recordings
import urllib.parse

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
    
def uploadFiles(drive_service):
    access_token = session.get('zoom_access_token')
    recordings = download_zoom_recordings(access_token)
    
    # Check if the "Automated Zoom Recordings" folder already exists
    results = drive_service.files().list(
        q="name='Automated Zoom Recordings' and mimeType='application/vnd.google-apps.folder'",
        fields='files(id)',
        spaces='drive'
    ).execute()

    if len(results['files']) > 0:
        recordings_folder_id = results['files'][0]['id']
    else:
        # Create the "Automated Zoom Recordings" folder if it doesn't exist
        file_metadata = {
            'name': 'Automated Zoom Recordings',
            'mimeType': 'application/vnd.google-apps.folder'
        }
        recordings_folder = drive_service.files().create(body=file_metadata, fields='id').execute()
        recordings_folder_id = recordings_folder['id']
        
    for recording in recordings:
        topics = recording['topic']
        folder_name = topics.replace(" ", "_")  # Replacing spaces with underscores
        folder_name = folder_name.replace("'", "\\'")  # Escape single quotation mark
        folder_id = None
        
        # Check if the folder already exists within "Automated Zoom Recordings"
        results = drive_service.files().list(
            q=f"name='{folder_name}' and '{recordings_folder_id}' in parents and mimeType='application/vnd.google-apps.folder'",
            fields='files(id)',
            spaces='drive'
        ).execute()

        if len(results['files']) > 0:
            folder_id = results['files'][0]['id']
        else:
            # Create the folder within "Automated Zoom Recordings" if it doesn't exist
            file_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder',
                'parents': [recordings_folder_id]
            }
            folder = drive_service.files().create(body=file_metadata, fields='id').execute()
            folder_id = folder['id']

        for files in recording['recording_files']:
            start_time = recording['start_time']
            start_datetime = datetime.strptime(start_time, "%Y-%m-%dT%H:%M:%SZ")
            date_string = start_datetime.strftime("%Y-%m-%d_%H-%M-%S")  # Updated format
            video_filename = f"{topics}_{date_string}.mp4"

            if files['status'] == 'completed' and files['file_extension'] == 'MP4' and recording['duration']>=10:
                download_url = files['download_url']
                response = requests.get(download_url)
                video_content = response.content
                video_filename = video_filename.replace("'", "\\'")  # Escape single quotation mark
                
                params=retrieve_parameters()
                accountName=params[0]
                accountName=params[1]
                
                if accountName in topics:
                    share_folder_with_email(drive_service, folder_id, email)
                    share_url = recording['share_url']  # Get the share_url from the recording
                    return share_url  # Return the share_url
    
                # Check if a file with the same name already exists in the folder
                query = f"name='{video_filename}' and '{folder_id}' in parents"
                existing_files = drive_service.files().list(
                    q=query,
                    fields='files(id)',
                    spaces='drive'
                ).execute()

                if len(existing_files['files']) > 0:
                    # File with the same name already exists, skip uploading
                    print(f"Skipping upload of '{video_filename}' as it already exists.")
                    continue

                # Upload the video to the folder in Google Drive
                file_metadata = {
                    'name': video_filename,
                    'parents': [folder_id]
                }
                media = MediaIoBaseUpload(io.BytesIO(video_content), mimetype='video/mp4')
                drive_service.files().create(
                    body=file_metadata,
                    media_body=media,
                    fields='id'
                ).execute()
                    
# Callback route after authentication
@upload_blueprint.route('/upload_callback')
def upload_callback():
    authorization_code = request.args.get('code')

    # Exchange the authorization code for a token
    flow.fetch_token(authorization_response=request.url)

    # Create a Google Drive service instance using the credentials
    credentials = flow.credentials
    drive_service = build('drive', API_VERSION, credentials=credentials)
    
    uploadFiles(drive_service)
    
    return "Recordings are being uploaded"
