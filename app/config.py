from __future__ import annotations
import os
import base64, json
from dataclasses import dataclass
from datetime import time

def _parse_time(s: str) -> time:
    h, m = map(int, s.split(":"))
    return time(h, m)

@dataclass(frozen=True)
class Config:
    notion_token: str
    notion_db_id: str
    gcal_id: str
    tz: str
    work_start: time
    work_end: time
    poll_interval_sec: int
    default_block_min: int
    oauth_client_file: str | None
    token_file: str | None
    oauth_client_json: dict | None
    token_json: dict | None

def load_config() -> Config:
    client_b64 = os.getenv("GOOGLE_OAUTH_CLIENT_B64")
    token_b64 = os.getenv("GOOGLE_TOKEN_B64")
    client_json = json.loads(base64.b64decode(client_b64)) if client_b64 else None
    token_json = json.loads(base64.b64decode(token_b64)) if token_b64 else None
    return Config(
        notion_token=os.getenv("NOTION_TOKEN",""),
        notion_db_id=os.getenv("NOTION_DATABASE_ID",""),
        gcal_id=os.getenv("GOOGLE_CALENDAR_ID","primary"),
        tz=os.getenv("TIMEZONE","America/Los_Angeles"),
        work_start=_parse_time(os.getenv("WORK_START","09:00")),
        work_end=_parse_time(os.getenv("WORK_END","18:00")),
        poll_interval_sec=int(os.getenv("POLL_INTERVAL_SEC","90")),
        default_block_min=int(os.getenv("DEFAULT_BLOCK_MIN","45")),
        oauth_client_file=os.getenv("GOOGLE_OAUTH_CLIENT_FILE"),
        token_file=os.getenv("GOOGLE_TOKEN_FILE"),
        oauth_client_json=client_json,
        token_json=token_json,
    )
