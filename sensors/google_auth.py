"""Google sign-in for the clinic account (Bruce, Module A).

First run opens a browser: log in as the CLINIC account and click Allow.
The token is saved to a file so you don't log in again (Testing mode tokens last 7 days).
Needs credentials.json downloaded from Google Cloud Console (OAuth client, type 'Desktop app').
"""
import os
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Read-only-ish scopes at onboarding. Both are 'restricted' scopes: fine in Testing mode.
BASIC_SCOPES = ["https://www.googleapis.com/auth/gmail.settings.basic",
                "https://www.googleapis.com/auth/drive.metadata.readonly"]
# Asked for only the first time someone taps 'Make private' (least privilege).
DRIVE_WRITE_SCOPES = ["https://www.googleapis.com/auth/drive"]

def get_creds(scopes=BASIC_SCOPES, token_file="token_basic.json"):
    creds = None
    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, scopes)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", scopes)
            creds = flow.run_local_server(port=0)
        with open(token_file, "w") as f:
            f.write(creds.to_json())
    return creds

def gmail(scopes=BASIC_SCOPES, token_file="token_basic.json"):
    return build("gmail", "v1", credentials=get_creds(scopes, token_file), cache_discovery=False)

def drive(scopes=BASIC_SCOPES, token_file="token_basic.json"):
    return build("drive", "v3", credentials=get_creds(scopes, token_file), cache_discovery=False)
