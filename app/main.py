from __future__ import annotations

from datetime import datetime, timedelta
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from dotenv import load_dotenv

from app.scheduler import start_scheduler, run_once
from app.config import load_config
from app.services.gcal import build_service, create_event
import pytz
from datetime import datetime, timedelta, timezone

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load .env and start background scheduler when the app starts
    load_dotenv()
    scheduler = start_scheduler()
    try:
        yield
    finally:
        # Stop scheduler cleanly on shutdown
        if scheduler:
            try:
                scheduler.shutdown(wait=False)
            except Exception:
                pass

app = FastAPI(
    title="Notion → Google Calendar Scheduler",
    lifespan=lifespan,
)

@app.get("/healthz")
async def healthz():
    return {"ok": True}

@app.post("/trigger")
async def trigger():
    try:
        result = await run_once()  # make run_once() return a dict summary
        return {"status": "ok", **(result or {})}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/test-event")
async def test_event():
    try:
        cfg = load_config()
        service = build_service(
            cfg.oauth_client_file, cfg.token_file, cfg.oauth_client_json, cfg.token_json
        )
        tz = pytz.timezone(cfg.tz)
        start_local = tz.localize(datetime.now() + timedelta(minutes=5))
        end_local = start_local + timedelta(minutes=10)
        eid = create_event(service, cfg.gcal_id, "MVP Test Event", start_local, end_local,
                        "Created by /test-event", tz=cfg.tz)
        return {"event_id": eid, "start": start_local.isoformat(), "end": end_local.isoformat()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
