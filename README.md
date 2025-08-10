# Notion → Google Calendar Scheduler (FastAPI MVP)

A FastAPI service that polls a Notion database for tasks, breaks them down, finds free time via Google Calendar FreeBusy, and creates events. Google Calendar syncs to Apple Calendar automatically if you've added your Google account to Apple Calendar.

## Quick start (local)

1) Python env
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2) Notion setup
- Create a Notion integration and share your database.
- Fields required (exact names): Task (Title), Due (Date), Planned? (Checkbox), Breakdown Needed? (Checkbox, optional), Estimated mins (Number, optional), Calendar Event IDs (Text).
- Copy `.env.example` to `.env` and fill NOTION_* values.

3) Google Calendar OAuth (one-time)
- In Google Cloud Console: enable **Google Calendar API**, create **OAuth Client (Desktop App)**, download `credentials.json`.
- Place it at `./secrets/credentials.json`.
- On first run, you'll be prompted to auth in the browser; `token.json` will be saved to `./secrets/token.json`.
  (For deployment, you can base64-encode these files into env vars.)

4) Run the service
```bash
uvicorn app.main:app --reload
```
- Health: http://localhost:8000/healthz
- Manual trigger: `POST /trigger`

## Deploying (Render/Railway/Lightsail)
- Set environment variables from `.env`.
- Provide `GOOGLE_OAUTH_CLIENT_B64` and `GOOGLE_TOKEN_B64` with base64 of the two JSON files (or mount them as files).
- Ensure the service has outbound internet.
- The APScheduler job will poll every `POLL_INTERVAL_SEC` seconds.

## Roadmap
- Two-way sync (calendar edits → Notion updates)
- Priority windows and energy-based scheduling
- Retry/backoff and better idempotency
