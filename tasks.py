import requests
import io
import redis
import json
import pickle
from celery import Celery
from datetime import datetime
import urllib.parse
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.oauth2 import credentials as google_credentials
from requests.exceptions import ConnectionError, ChunkedEncodingError

# Create a Celery instance
celery = Celery('task', broker='redis://default:2qCxa3AEmJTH61oG4oa8@containers-us-west-90.railway.app:7759')
redis_client = redis.from_url("redis://default:2qCxa3AEmJTH61oG4oa8@containers-us-west-90.railway.app:7759")

CHUNK_SIZE = 1024 * 1024

@celery.task(bind=True, max_retries=3)
def uploadFiles(self, serialized_credentials, recordings):
    try:
        credentials = pickle.loads(serialized_credentials)
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
            
            folder_urls_data = redis_client.get("folder_urls")
            if folder_urls_data:
                existing_folder_urls = json.loads(folder_urls_data)
            else:
                existing_folder_urls = {}
                
            # Retrieve the stored_params dictionary from Redis
            stored_params_data = redis_client.get("stored_params")
            if stored_params_data:
                stored_params = json.loads(stored_params_data)
            else:
                stored_params = {}
                
            # Check if the accountName is in the topic
            for accountName, email in stored_params.items():
                if accountName is not None and email is not None:
                    if accountName in topics and accountName not in existing_folder_urls:
                        # Share the folder with the email
                        folder_url = share_folder_with_email(drive_service, folder_name, email, recordings_folder_id)
                        existing_folder_urls[accountName] = folder_url
                
            # Store the updated data back into the Redis database
            redis_client.set("folder_urls", json.dumps(existing_folder_urls))

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
                download_url = files['download_url']
                
                if files['status'] == 'completed' and files['file_extension'] == 'MP4' and recording['duration'] >= 10:
                    try:
                        response = requests.get(download_url, stream=True)

                        # Stream the video content in chunks and store in the video_content BytesIO object
                        for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                            if chunk:
                                video_content.write(chunk)

                        # Close the response to release resources
                        response.close()

                    except (ConnectionError, ChunkedEncodingError) as e:
                        print(f"Error occurred while downloading recording: {str(e)}")
                        self.retry(countdown=10)  # Retry after 10 seconds

            if video_content.tell() > 0:
                # Upload the video to the folder in Google Drive
                file_metadata = {
                    'name': video_filename,
                    'parents': [folder_id]
                }

                video_content.seek(0)
                media = MediaIoBaseUpload(
                    video_content,
                    mimetype='video/mp4',
                    chunksize=CHUNK_SIZE,
                    resumable=True
                )

                request = drive_service.files().create(
                    body=file_metadata,
                    media_body=media,
                    fields='id',
                    supportsTeamDrives=True
                )
                response = None
                while response is None:
                    _, response = request.next_chunk()

                print(f"Video '{video_filename}' uploaded successfully.")
    except Exception as e:
        print(f"An error occurred: {str(e)}")

def share_folder_with_email(drive_service, folder_name, email, recordings_folder_id):
    # Check if the folder already exists within "Automated Zoom Recordings"
    results = drive_service.files().list(
        q=f"name='{folder_name}' and '{recordings_folder_id}' in parents and mimeType='application/vnd.google-apps.folder'",
        fields='files(id, webViewLink)',
        spaces='drive'
    ).execute()

    if len(results['files']) > 0:
        folder_id = results['files'][0]['id']
        folder_web_view_link = results['files'][0]['webViewLink']
    else:
        # Create the folder within "Automated Zoom Recordings" if it doesn't exist
        file_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [recordings_folder_id]
        }
        folder = drive_service.files().create(body=file_metadata, fields='id, webViewLink').execute()
        folder_id = folder['id']
        folder_web_view_link = folder['webViewLink']

    # Share the folder with the email
    permission_metadata = {
        'type': 'user',
        'role': 'writer',
        'emailAddress': email
    }
    drive_service.permissions().create(
        fileId=folder_id,
        body=permission_metadata,
        fields='id'
    ).execute()

    return folder_web_view_link
