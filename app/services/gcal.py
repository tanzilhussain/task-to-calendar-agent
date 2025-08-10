from __future__ import annotations
from datetime import datetime, timedelta
from typing import List, Tuple, Optional
import os, json

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request


SCOPES = ["https://www.googleapis.com/auth/calendar"]

def _load_creds(oauth_client_file: str | None, token_file: str | None, oauth_client_json: dict | None, token_json: dict | None) -> Credentials:
    creds = None
    if token_json:
        creds = Credentials.from_authorized_user_info(token_json, SCOPES)
    elif token_file and os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if oauth_client_json:
                flow = InstalledAppFlow.from_client_config(oauth_client_json, SCOPES)
            elif oauth_client_file:
                flow = InstalledAppFlow.from_client_secrets_file(oauth_client_file, SCOPES)
            else:
                raise RuntimeError("No OAuth client provided")
            creds = flow.run_local_server(port=0)
        if token_file:
            os.makedirs(os.path.dirname(token_file), exist_ok=True)
            with open(token_file, "w") as f:
                f.write(creds.to_json())
    return creds

def build_service(oauth_client_file: str | None, token_file: str | None, oauth_client_json: dict | None, token_json: dict | None):
    creds = _load_creds(oauth_client_file, token_file, oauth_client_json, token_json)
    return build("calendar", "v3", credentials=creds, cache_discovery=False)

from datetime import datetime
from typing import List, Tuple
import pytz  # add this import

def freebusy(service, calendar_id: str, start: datetime, end: datetime, tz: str = "UTC") -> List[Tuple[datetime, datetime]]:
    # Ensure start/end are tz-aware
    if start.tzinfo is None or end.tzinfo is None:
        raise ValueError("freebusy requires tz-aware datetimes")
    body = {
        "timeMin": start.isoformat(),
        "timeMax": end.isoformat(),
        "timeZone": tz,
        "items": [{"id": calendar_id}],
    }
    resp = service.freebusy().query(body=body).execute()
    periods = resp["calendars"][calendar_id].get("busy", [])
    out = []
    local_tz = pytz.timezone(tz)
    for p in periods:
        # Google returns ISO with tz; normalize to local tz for comparisons
        s = datetime.fromisoformat(p["start"]).astimezone(local_tz)
        e = datetime.fromisoformat(p["end"]).astimezone(local_tz)
        out.append((s, e))
    return out

def create_event(service, calendar_id: str, title: str,
                 start: datetime, end: datetime,
                 description: str = "", tz: str = "UTC") -> str:
    if start.tzinfo is None or end.tzinfo is None:
        raise ValueError("create_event requires tz-aware datetimes")
    body = {
        "summary": title,
        "description": description,
        "start": {"dateTime": start.isoformat(), "timeZone": tz},
        "end":   {"dateTime": end.isoformat(),   "timeZone": tz},
    }
    ev = service.events().insert(calendarId=calendar_id, body=body).execute()
    return ev["id"]
