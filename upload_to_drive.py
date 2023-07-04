from flask import Blueprint, session
from datetime import datetime
import io
import os
import requests
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

upload_blueprint = Blueprint('upload', __name__)
upload_blueprint.secret_key = '@unblinded2018'
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

@upload_blueprint.route('/upload_callback')
def upload():
    access_token = session.get('zoom_access_token')
    recordings_data = download_zoom_recordings(access_token)

    # Step 1: Authenticate and authorize API access
    credentials = get_credentials()
    drive_service = build('drive', 'v3', credentials=credentials)

    # Step 2: Check if the 'Automated Zoom Recordings' folder exists in Google Drive, create it if not
    automated_folder_name = 'Automated Zoom Recordings'
    automated_folder_id = get_folder_id(drive_service, automated_folder_name)

    if not automated_folder_id:
        # Create the 'Automated Zoom Recordings' folder in Google Drive
        automated_folder_id = create_folder(drive_service, automated_folder_name)
        print(f'Folder "{automated_folder_name}" created in Google Drive with ID: {automated_folder_id}')

    # Dictionary to store parent folder IDs
    parent_folders = {'Automated Zoom Recordings': automated_folder_id}

    # Define a function to upload a video file
    def upload_video(file_metadata, file_content, folder_id):
        media = MediaIoBaseUpload(io.BytesIO(file_content), mimetype='video/mp4')
        file = drive_service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()
        file_id = file['id']
        print(f'Video file "{file_metadata["name"]}" uploaded to the folder with ID: {file_id}')

    # Iterate over each recording in the JSON data
    for recording in recordings_data:
        # Extract necessary information from the recording
        for file in recording['recording_files']:
            # Check if the status is completed and the file extension is MP4
            if file['status'] == 'completed' and file['file_extension'] == 'MP4':
                topic = recording['topic']
                start_time = recording['start_time']
                start_datetime = datetime.strptime(start_time, "%Y-%m-%dT%H:%M:%SZ")
                date_string = start_datetime.strftime("%Y-%m-%d_%H-%M-%S")  # Updated format
                video_filename = f"{topic}_{date_string}.mp4"
                folder_name = topic.replace(" ", "_")  # Replacing spaces with underscores
                download_url = file['download_url']

                folder_exists = False
                folder_name = folder_name.replace("'", "\\'")  # Escape single quotation mark

                # Check if the parent folder exists in the parent_folders dictionary
                if folder_name in parent_folders:
                    # Use the existing parent folder ID
                    parent_id = parent_folders[folder_name]
                else:
                    # Check if the folder already exists within the parent folder
                    parent_id = get_folder_id(drive_service, folder_name, automated_folder_id)

                    if parent_id:
                        parent_folders[folder_name] = parent_id
                        print(f'Folder "{folder_name}" already exists in Google Drive with ID: {parent_id}')
                    else:
                        # Create the parent folder in Google Drive
                        parent_id = create_folder(drive_service, folder_name, automated_folder_id)
                        parent_folders[folder_name] = parent_id
                        print(f'Folder "{folder_name}" created in Google Drive with ID: {parent_id}')

                # Step 5: Download the video file to in-memory storage
                response = requests.get(download_url)
                file_content = response.content
                # Step 6: Upload the video file to the folder in Google Drive
                file_exists = False
                video_filename = video_filename.replace("'", "\\'")  # Escape single quotation mark

                file_id = get_file_id(drive_service, video_filename, parent_id)
                if file_id:
                    file_exists = True
                    print(f'Video file "{video_filename}" already exists in the folder with ID: {file_id}')

                if not file_exists:
                    # Upload the video file to the folder in Google Drive
                    file_metadata = {
                        'name': video_filename,
                        'parents': [parent_id]
                    }
                    upload_video(file_metadata, file_content, parent_id)

    return 'Upload completed!'


def get_credentials():
    # Replace with your client_id and client_secret from the Google Cloud Console
    client_id = '21876034997-mjfsr5ojhnrmspao3ud5er3babhtvn0s.apps.googleusercontent.com'
    client_secret = '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'
    scopes = ['https://www.googleapis.com/auth/drive']
    redirect_uri = 'https://flask-production-d5a3.up.railway.app/upload_callback'

    flow = Flow.from_client_secrets_file(
        'client_secret.json',
        scopes=scopes,
        redirect_uri=redirect_uri
    )
    auth_url, _ = flow.authorization_url(prompt='consent')

    # Redirect the user to the auth_url and get the authorization code from the callback URL
    # Handle the authorization code exchange to obtain the access token
    # Return the credentials object
    # See the Google Auth Python library documentation for detailed instructions: https://google-auth.readthedocs.io/en/latest/

    return credentials


def get_folder_id(drive_service, folder_name, parent_folder_id=None):
    query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    if parent_folder_id:
        query += f" and '{parent_folder_id}' in parents"
    response = drive_service.files().list(q=query, fields='files(id)').execute()
    folders = response.get('files', [])
    if folders:
        return folders[0]['id']
    return None


def create_folder(drive_service, folder_name, parent_folder_id=None):
    folder_metadata = {
        'name': folder_name,
        'mimeType': 'application/vnd.google-apps.folder'
    }
    if parent_folder_id:
        folder_metadata['parents'] = [parent_folder_id]

    folder = drive_service.files().create(body=folder_metadata, fields='id').execute()
    return folder['id']


def get_file_id(drive_service, file_name, folder_id):
    query = f"name='{file_name}' and '{folder_id}' in parents and trashed=false"
    response = drive_service.files().list(q=query, fields='files(id)').execute()
    files = response.get('files', [])
    if files:
        return files[0]['id']
    return None
