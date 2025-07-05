import os.path

from google.oauth2 import service_account
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from io import BytesIO
from googleapiclient.errors import HttpError

import json
import os

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/drive.metadata.readonly"]

def get_drive_service():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    else:
        flow = InstalledAppFlow.from_client_secrets_file('-token.json', SCOPES)
        creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    return build('drive', 'v3', credentials=creds)

def get_drive_service2():
    client = os.environ.get('GDCLIENT', None)
    if client is None:
        client = 'gdrive-client.json'
        creds = service_account.Credentials.from_service_account_file(
            client, scopes=SCOPES)
    else:
        client = json.loads(client)
        client['private_key'] = client['private_key'].replace('\\n','\n')
        creds = service_account.Credentials.from_service_account_info(client, scopes=SCOPES)
    return build('drive', 'v3', credentials=creds)

def list_product_folders(service, parent_folder_id):
    query = f"'{parent_folder_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed = false"
    results = service.files().list(q=query, fields="files(id, name)").execute()
    return results.get('files', [])

def get_folder_files(service, folder_id):
    query = f"'{folder_id}' in parents and trashed = false"
    results = service.files().list(q=query, fields="files(id, name, mimeType, webViewLink)").execute()
    return results.get('files', [])

def read_text_file(service, file_id):
    request = service.files().get_media(fileId=file_id)
    fh = BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        status, done = downloader.next_chunk()
    return fh.getvalue().decode('utf-8')

def parse_product_info(folder_name):
    try:
        name, price = folder_name.rsplit('_', 1)
        return name.strip(), price.strip()
    except ValueError:
        return folder_name, "N/A"

def fetch_product_data(service, parent_folder_id):
    products = []
    folders = list_product_folders(service, parent_folder_id)
    for folder in folders:
        name, price = parse_product_info(folder['name'])
        files = get_folder_files(service, folder['id'])

        images = []
        description = ""

        for file in files:
            if 'image' in file['mimeType']:
                images.append(file['webViewLink'])
            elif file['name'].endswith('.txt'):
                description = file['name']

        products.append({
            'name': name,
            'price': price,
            'images': images,
            'description': description
        })

    return products