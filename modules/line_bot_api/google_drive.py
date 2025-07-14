import os.path
import base64

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
from datetime import datetime

# If modifying these scopes, delete the file token.json.
SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/spreadsheets"
]

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
        client['private_key'] = client['private_key'].replace('\n','\n')
        creds = service_account.Credentials.from_service_account_info(client, scopes=SCOPES)
    return build('drive', 'v3', credentials=creds)

def list_product_folders(service, parent_folder_id):
    query = f"'{parent_folder_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed = false"
    results = service.files().list(q=query, fields="files(id, name)").execute()
    return results.get('files', [])

def get_orderList(service, parent_folder_id):
    query = f"'{parent_folder_id}' in parents and name = 'OrderList' and mimeType='application/vnd.google-apps.spreadsheet' and trashed = false"
    results = service.files().list(q=query, fields="files(id, name)").execute()
    files = results.get('files', [])
    if files:
        return files[0]['id']
    return None

def get_folder_files(service, folder_id):
    query = f"'{folder_id}' in parents and trashed = false"
    results = service.files().list(q=query, fields="files(id, name, mimeType, webViewLink, webContentLink)").execute()
    return results.get('files', [])

def read_text_file(service, file_id):
    request = service.files().get_media(fileId=file_id)
    fh = BytesIO()
    downloader = MediaIoBaseDownload(fh, request);
    done = False
    while not done:
        status, done = downloader.next_chunk()
    return fh.getvalue().decode('utf-8')

def download_image_as_base64(service, file_id):
    request = service.files().get_media(fileId=file_id)
    fh = BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        status, done = downloader.next_chunk()
    fh.seek(0)
    return base64.b64encode(fh.getvalue()).decode('utf-8')

def parse_product_info(folder_name):
    return folder_name, "N/A"

def fetch_product_data(service, parent_folder_id):
    products = []
    folders = list_product_folders(service, parent_folder_id)
    for folder in folders:
        files = get_folder_files(service, folder['id'])

        images = []
        description = ""

        for file in files:
            if 'image' in file['mimeType']:
                images.append(download_image_as_base64(service, file['id']))
            elif file['name'].endswith('.txt'):
                description = read_text_file(service, file['id'])

        products.append({
            'name': folder['name'],
            'images': images,
            'description': description
        })

    return products

def get_sheets_service():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    else:
        flow = InstalledAppFlow.from_client_secrets_file('gdrive-client.json', SCOPES)
        creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return build('sheets', 'v4', credentials=creds)

def submit_order(service, name, contact, pickup_time, items, sheet_id):
    spreadsheet_id = sheet_id
    range_name = 'Sheet1!A:G'  # Assuming data starts from A1 and goes up to G column (for new fields)

    values = []
    for item in items:
        values.append([
            name, 
            contact, 
            item['productName'], 
            item['option'], 
            item['price'], 
            item['quantity'], 
            pickup_time, 
            str(datetime.now())
        ])

    body = {
        'values': values
    }
    result = service.spreadsheets().values().append(
        spreadsheetId=spreadsheet_id, range=range_name,
        valueInputOption='USER_ENTERED', body=body).execute()
    return result.get('updates', {}).get('updatedCells')

def get_sheets_service2():
    client = os.environ.get('GDCLIENT', None)
    if client is None:
        client = 'gdrive-client.json'
        creds = service_account.Credentials.from_service_account_file(
            client, scopes=SCOPES)
    else:
        client = json.loads(client)
        client['private_key'] = client['private_key'].replace('\n','\n')
        creds = service_account.Credentials.from_service_account_info(client, scopes=SCOPES)
    return build('sheets', 'v4', credentials=creds)

def get_price_list(drive_service, sheets_service, parent_folder_id, product_name):
    price_list = []
    try:
        # Find the specific product folder
        query = f"'{parent_folder_id}' in parents and name = '{product_name}' and mimeType='application/vnd.google-apps.folder' and trashed = false"
        results = drive_service.files().list(q=query, fields="files(id)").execute()
        folders = results.get('files', [])
        if not folders:
            print(f"Warning: Product folder '{product_name}' not found.")
            return []
        product_folder_id = folders[0]['id']

        # Find the 'price' spreadsheet within that folder
        query = f"'{product_folder_id}' in parents and name = 'price' and mimeType='application/vnd.google-apps.spreadsheet' and trashed = false"
        results = drive_service.files().list(q=query, fields="files(id)").execute()
        files = results.get('files', [])
        if not files:
            print(f"Warning: 'price' spreadsheet not found in '{product_name}' folder.")
            return []
        spreadsheet_id = files[0]['id']

        # Get the first sheet's title
        sheet_metadata = sheets_service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        sheets = sheet_metadata.get('sheets', [])
        if not sheets:
            print(f"Warning: No sheets found in 'price' spreadsheet for '{product_name}'.")
            return []
        sheet_title = sheets[0].get('properties', {}).get('title', 'Sheet1')

        # Read the spreadsheet data
        result = sheets_service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=sheet_title
        ).execute()
        values = result.get('values', [])

        if not values:
            print(f"Warning: 'price' spreadsheet for '{product_name}' is empty.")
            return []

        # Find column indices from header
        header = values[0]
        try:
            option_col = header.index("品項") # Now treated as option
            price_col = header.index("價格")
        except ValueError:
            print(f"Warning: '品項' or '價格' column not found in 'price' spreadsheet for '{product_name}'.")
            return []

        # Create the price list
        for row in values[1:]:
            if len(row) > max(option_col, price_col) and row[option_col]:
                option = row[option_col]
                price = row[price_col]
                price_list.append({'option': option, 'price': price})

    except HttpError as err:
        print(f"Error accessing price sheet for '{product_name}': {err}")
    
    return price_list
