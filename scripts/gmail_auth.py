from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

_BASE_DIR = Path(__file__).resolve().parent.parent
CREDENTIALS_PATH = _BASE_DIR / "credentials.json"
TOKEN_PATH = _BASE_DIR / "token.json"


def gmail_authenticate() -> Credentials:
    creds = None

    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                str(CREDENTIALS_PATH), SCOPES
            )
            creds = flow.run_local_server(port=0)

        TOKEN_PATH.write_text(creds.to_json())

    return creds


if __name__ == "__main__":
    credentials = gmail_authenticate()
    print(f"Authenticated successfully.\nScopes: {credentials.scopes}")
