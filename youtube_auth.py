import pickle
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import os

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube"
]

TOKEN_FILE    = "youtube_token.pickle"
CLIENT_SECRET = "client_secret.json"

def authenticate():
    creds = None

    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "rb") as f:
            creds = pickle.load(f)

    if creds and creds.valid:
        print("✅ Already authenticated!")
        return creds

    if creds and creds.expired and creds.refresh_token:
        print("🔄 Refreshing token...")
        creds.refresh(Request())
    else:
        print("🌐 Opening browser for Google login...")
        flow  = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET, SCOPES)
        creds = flow.run_local_server(port=0)

    with open(TOKEN_FILE, "wb") as f:
        pickle.dump(creds, f)

    print("✅ Authentication successful!")
    print(f"✅ Token saved to {TOKEN_FILE}")
    return creds

if __name__ == "__main__":
    authenticate()