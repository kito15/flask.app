import io
import pickle
import redis
import json
import requests
from celery import Celery
from datetime import datetime
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.oauth2 import credentials as google_credentials
from requests.exceptions import ConnectionError, ChunkedEncodingError

# Create a Celery instance
celery = Celery('task', broker='redis://default:2qCxa3AEmJTH61oG4oa8@containers-us-west-90.railway.app:7759')
redis_client = redis.from_url("redis://default:2qCxa3AEmJTH61oG4oa8@containers-us-west-90.railway.app:7759")

@celery.task(bind=True, max_retries=3)
def uploadFiles(self, serialized_credentials, recordings):
    try:
        credentials = pickle.loads(serialized_credentials)
        API_VERSION = 'v3'
        drive_service = build('drive', API_VERSION, credentials=credentials)

        # Check if the "Automated Zoom Recordings" folder already exists
        recordings_folder_id = get_or_create_folder(drive_service, 'Automated Zoom Recordings')

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
            folder_id = get_or_create_folder(drive_service, folder_name, recordings_folder_id)

            for files in recording['recording_files']:
                start_time = recording['start_time']
                start_datetime = datetime.strptime(start_time, "%Y-%m-%dT%H:%M:%SZ")
                date_string = start_datetime.strftime("%Y-%m-%d_%H-%M-%S")  # Updated format
                video_filename = f"{topics}_{date_string}.mp4"
                download_url = files['download_url']

                if files['status'] == 'completed' and files['file_extension'] == 'MP4' and recording['duration'] >= 10:
                    try:
                        response = requests.get(download_url)
                        response.raise_for_status()
                        video_content = response.content
                        video_filename = video_filename.replace("'", "\\'")  # Escape single quotation mark

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

                    except (ConnectionError, ChunkedEncodingError) as e:
                        print(f"Error occurred while downloading recording: {str(e)}")
                        self.retry(countdown=10)  # Retry after 10 seconds

    except Exception as e:
        print(f"An error occurred: {str(e)}")

def get_or_create_folder(drive_service, folder_name, parent_folder_id=None):
    if parent_folder_id:
        query = f"name='{folder_name}' and '{parent_folder_id}' in parents and mimeType='application/vnd.google-apps.folder'"
    else:
        query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder'"

    results = drive_service.files().list(
        q=query,
        fields='files(id)',
        spaces='drive'
    ).execute()

    if len(results['files']) > 0:
        return results['files'][0]['id']
    else:
        if parent_folder_id:
            file_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder',
                'parents': [parent_folder_id]
            }
        else:
            file_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }

        folder = drive_service.files().create(body=file_metadata, fields='id').execute()
        return folder['id']

def share_folder_with_email(drive_service, folder_name, email, recordings_folder_id):
    folder_id = get_or_create_folder(drive_service, folder_name, recordings_folder_id)

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

    results = drive_service.files().get(
        fileId=folder_id,
        fields='webViewLink',
        supportsAllDrives=True
    ).execute()

    return results['webViewLink']
