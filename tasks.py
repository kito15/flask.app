import json
import os
import requests
import io
import tempfile
from celery import Celery
from datetime import datetime
import urllib.parse
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.oauth2 import credentials as google_credentials

# Create a Celery instance
celery = Celery('task',broker='redis://default:2qCxa3AEmJTH61oG4oa8@containers-us-west-90.railway.app:7759')

@celery.task
def uploadFiles(credentials_dict,recordings,accountName,email):
    
    credentials = google_credentials.Credentials.from_authorized_user_info(credentials_dict)
    API_VERSION = 'v3'
    drive_service = build('drive', API_VERSION, credentials=credentials)
     
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
                
                if accountName in topics:
                    """share_folder_with_email(drive_service, folder_id, email)"""
                    share_url = recording['share_url']  # Get the share_url from the recording
                    """return share_url"""
                
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
