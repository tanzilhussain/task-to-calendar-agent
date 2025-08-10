# scripts/auth_gcal.py
from dotenv import load_dotenv
load_dotenv()

from app.config import load_config
from app.services.gcal import build_service

cfg = load_config()
service = build_service(cfg.oauth_client_file, cfg.token_file, cfg.oauth_client_json, cfg.token_json)
print("✅ Google Calendar auth OK. Token saved at:", cfg.token_file or "<env token>")
