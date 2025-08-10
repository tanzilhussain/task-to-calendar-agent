from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional
import re

@dataclass
class Subtask:
    title: str
    minutes: int

DEEP = ("write","design","study","research","draft","analyze","build")
LIGHT = ("email","call","review","read","plan","outline","clean")

def estimate_minutes(title: str, override: Optional[int]) -> int:
    if override: return max(15, min(override, 120))
    t = title.lower()
    if any(v in t for v in DEEP): return 60
    if any(v in t for v in LIGHT): return 25
    return 45

def breakdown(task_title: str, breakdown_needed: bool, override: Optional[int]) -> List[Subtask]:
    if not breakdown_needed:
        return [Subtask(task_title, estimate_minutes(task_title, override))]
    parts = re.split(r"\band\b|;|:", task_title, flags=re.IGNORECASE)
    parts = [p.strip(" -–—•") for p in parts if p and p.strip()]
    parts = parts[:6] if parts else [task_title]
    return [Subtask(p, estimate_minutes(p, override)) for p in parts]
