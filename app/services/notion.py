from __future__ import annotations
from typing import List, Dict, Any
from notion_client import Client

PLANNED_PROP = "Planned?"
DUE_PROP = "Due"
TITLE_PROP = "Task"
EVENT_IDS_PROP = "Calendar Event IDs"
BREAKDOWN_PROP = "Breakdown Needed?"
EST_MIN_PROP = "Estimated mins"
NOTES_PROP = "Notes"

class NotionTasks:
    def __init__(self, token: str, database_id: str):
        self.client = Client(auth=token)
        self.db = database_id

    def fetch_new(self) -> List[Dict[str,Any]]:
        res = self.client.databases.query(
            **{
                "database_id": self.db,
                "filter": {"and": [
                    {"property": PLANNED_PROP, "checkbox": {"equals": False}},
                    {"property": DUE_PROP, "date": {"is_not_empty": True}},
                ]},
                "page_size": 50,
            }
        )
        return res.get("results", [])

    def title_of(self, page: Dict[str,Any]) -> str:
        title = page["properties"][TITLE_PROP]["title"]
        return "".join([t.get("plain_text","") for t in title]) if title else "Untitled"

    def due_of(self, page: Dict[str,Any]) -> str | None:
        date = page["properties"][DUE_PROP].get("date")
        return date.get("start") if date else None

    def est_of(self, page: Dict[str,Any]) -> int | None:
        num = page["properties"].get(EST_MIN_PROP, {}).get("number")
        return int(num) if num else None

    def notes_of(self, page: Dict[str, Any]) -> str | None:
        prop = page["properties"].get(NOTES_PROP)
        if not prop:
            return None
        rich = prop.get("rich_text", [])
        return "".join([r.get("plain_text", "") for r in rich]) or None
    
    def needs_breakdown(self, page: Dict[str,Any]) -> bool:
        return bool(page["properties"].get(BREAKDOWN_PROP, {}).get("checkbox"))

    def mark_planned(self, page_id: str, event_ids: list[str]) -> None:
        self.client.pages.update(**{
            "page_id": page_id,
            "properties": {
                PLANNED_PROP: {"checkbox": True},
                EVENT_IDS_PROP: {"rich_text":[{"type":"text","text":{"content":",".join(event_ids)}}]},
            }
        })
