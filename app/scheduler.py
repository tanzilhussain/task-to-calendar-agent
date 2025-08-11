from __future__ import annotations
from datetime import datetime, timedelta, time
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import pytz

from app.config import load_config
from app.services.notion import NotionTasks
from app.services.planner import breakdown
from app.services.gcal import build_service, freebusy, create_event
from app.services.storage import make_session, Item, Event

from dateutil import parser as dtparser

def within_workday(dt: datetime, start: time, end: time, tzname: str) -> tuple[datetime, datetime]:
    tz = pytz.timezone(tzname)
    # ensure dt is tz-aware in your local tz
    if dt.tzinfo is None:
        local = tz.localize(dt)
    else:
        local = dt.astimezone(tz)
    day_start = local.replace(hour=start.hour, minute=start.minute, second=0, microsecond=0)
    day_end   = local.replace(hour=end.hour, minute=end.minute, second=0, microsecond=0)
    return day_start, day_end

def find_gap(busy, day_start, day_end, minutes, buffer_min=5):
    cur = day_start
    need = timedelta(minutes=minutes)
    buf = timedelta(minutes=buffer_min)
    for b_start, b_end in busy:
        if b_end <= cur:
            continue
        if b_start - cur >= need:
            return cur, cur + need
        cur = max(cur, b_end + buf)
        if cur >= day_end:
            return None
    if day_end - cur >= need:
        return cur, cur + need
    return None

async def run_once():
    cfg = load_config()
    tz = pytz.timezone(cfg.tz)

    notion = NotionTasks(cfg.notion_token, cfg.notion_db_id)
    service = build_service(cfg.oauth_client_file, cfg.token_file, cfg.oauth_client_json, cfg.token_json)
    session = make_session()

    pages = notion.fetch_new()
    created_total = 0
    processed = []

    # cursor starts NOW in your local tz
    cursor = datetime.now(tz)

    for page in pages:
        page_id = page["id"]
        title = notion.title_of(page)
        due_iso = notion.due_of(page)
        if not due_iso:
            continue

        # Parse due; if Notion gives naive date, localize it
        due = dtparser.isoparse(due_iso)
        if due.tzinfo is None:
            due = tz.localize(due)
        else:
            due = due.astimezone(tz)

        notes = None
        try:
            notes = notion.notes_of(page)
        except Exception:
            pass
        subs = breakdown(title, notion.needs_breakdown(page), notion.est_of(page), notes=notes)

        created_ids = []

        for s in subs:
            # Search day-by-day until due
            window = cursor
            scheduled = False
            while window <= due:
                day_start, day_end = within_workday(window, cfg.work_start, cfg.work_end, cfg.tz)
                # Ensure we start no earlier than 'cursor'
                start_from = max(cursor, day_start)

                # Free/busy in local tz
                busy = freebusy(service, cfg.gcal_id, day_start, day_end, tz=cfg.tz)
                gap = find_gap(busy, start_from, day_end, s.minutes)

                if gap:
                    start, end = gap
                    eid = create_event(service, cfg.gcal_id, f"{title} — {s.title}", start, end,
                                       description="Auto-scheduled from Notion", tz=cfg.tz)
                    created_ids.append(eid)
                    created_total += 1
                    cursor = end + timedelta(minutes=5)
                    scheduled = True
                    break

                # go to next day
                window = day_start + timedelta(days=1)

            if not scheduled:
                # overflow: place first slot the day after due
                day_start, day_end = within_workday(due + timedelta(days=1), cfg.work_start, cfg.work_end, cfg.tz)
                busy = freebusy(service, cfg.gcal_id, day_start, day_end, tz=cfg.tz)
                gap = find_gap(busy, day_start, day_end, s.minutes) or (day_start, day_start + timedelta(minutes=s.minutes))
                start, end = gap
                eid = create_event(service, cfg.gcal_id, f"⚠️ {title} — {s.title}", start, end,
                                   description="Auto-scheduled (overflow) from Notion", tz=cfg.tz)
                created_ids.append(eid)
                created_total += 1
                cursor = end + timedelta(minutes=5)

        notion.mark_planned(page_id, created_ids)
        processed.append({"page_id": page_id, "title": title, "events": created_ids})

    return {"pages_fetched": len(pages), "events_created": created_total, "processed": processed}


def start_scheduler():
    cfg = load_config()
    scheduler = AsyncIOScheduler()
    scheduler.add_job(run_once, "interval", seconds=cfg.poll_interval_sec, id="poller", max_instances=1, coalesce=True)
    scheduler.start()
    return scheduler
