from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional
import os, re, json, logging

# Optional: Gemini AI
try:
    import google.generativeai as genai  # pip install google-generativeai
except Exception:  # pragma: no cover
    genai = None

log = logging.getLogger("planner")

@dataclass
class Subtask:
    title: str
    minutes: int

# --------- Fallback heuristics (your original logic) ---------
DEEP = ("write", "design", "study", "research", "draft", "analyze", "build")
LIGHT = ("email", "call", "review", "read", "plan", "outline", "clean")

def _estimate_minutes_rule(title: str, override: Optional[int]) -> int:
    if override:
        return max(15, min(int(override), 120))
    t = title.lower()
    if any(v in t for v in DEEP): return 60
    if any(v in t for v in LIGHT): return 25
    return 45

def _fallback_breakdown(task_title: str, breakdown_needed: bool, override: Optional[int]) -> List[Subtask]:
    if not breakdown_needed:
        return [Subtask(task_title, _estimate_minutes_rule(task_title, override))]
    parts = re.split(r"\band\b|;|:", task_title, flags=re.IGNORECASE)
    parts = [p.strip(" -–—•") for p in parts if p and p.strip()]
    parts = parts[:6] if parts else [task_title]
    return [Subtask(p, _estimate_minutes_rule(p, override)) for p in parts]

# --------- Gemini-backed planner ---------
def _call_gemini(task_title: str,
                 breakdown_needed: bool,
                 override: Optional[int],
                 notes: Optional[str] = None,
                 max_subtasks: int = 6) -> List[Subtask]:
    """
    Ask Gemini for a JSON plan. Returns Subtask[].
    Falls back to heuristics if API key missing, errors, or bad output.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or genai is None:
        return _fallback_breakdown(task_title, breakdown_needed, override)

    try:
        genai.configure(api_key=api_key)
        # choose a stable, capable model; change if you prefer a different one
        model = genai.GenerativeModel("gemini-1.5-pro")

        # System/style guidance
        sys = (
            "You are a time-planning assistant. "
            "Given a task (and optional notes), decide whether to split it and estimate how long each subtask should take. "
            "Return JSON only, no prose, in the format: "
            "{\"subtasks\":[{\"title\":\"...\",\"minutes\":45}, ...]}. "
            "Constrain each 'minutes' to 15..120. Prefer splitting deep work into 25–60 minute chunks. "
            f"Limit subtasks to at most {max_subtasks}. "
            "If the user didn't request a breakdown, you may still adjust the single estimate but keep one item."
        )

        user_payload = {
            "task_title": task_title,
            "breakdown_requested": bool(breakdown_needed),
            "estimate_override_minutes": int(override) if override else None,
            "notes": (notes or "").strip(),
        }

        prompt = (
            f"{sys}\n\n"
            f"INPUT:\n{json.dumps(user_payload, ensure_ascii=False)}\n\n"
            "OUTPUT JSON ONLY:\n"
            "{\"subtasks\":[{\"title\":\"...\",\"minutes\":45}]}"
        )

        resp = model.generate_content(prompt)
        text = (resp.candidates[0].content.parts[0].text if resp and resp.candidates else "").strip()

        # Extract JSON block
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1:
            raise ValueError("Gemini did not return JSON")
        data = json.loads(text[start:end+1])
        items = data.get("subtasks", [])
        if not isinstance(items, list) or not items:
            raise ValueError("No subtasks in JSON")

        out: List[Subtask] = []
        for it in items[:max_subtasks]:
            title = str(it.get("title", "")).strip() or task_title
            # minutes with bounds + override respected
            try:
                minutes = int(it.get("minutes", 0))
            except Exception:
                minutes = 0
            if override:
                minutes = max(15, min(int(override), 120))
            else:
                minutes = max(15, min(minutes, 120))
            out.append(Subtask(title=title, minutes=minutes))

        if not out:
            return _fallback_breakdown(task_title, breakdown_needed, override)

        # Respect user's checkbox: if breakdown not requested, collapse to a single estimate
        if not breakdown_needed and len(out) > 1:
            # choose the longest suggested chunk as the single focused block (or just first)
            out.sort(key=lambda s: s.minutes, reverse=True)
            return [out[0]]

        return out

    except Exception as e:
        log.warning("Gemini plan failed; using fallback. err=%s", e)
        return _fallback_breakdown(task_title, breakdown_needed, override)

# --------- Public API (used by scheduler) ---------
def estimate_minutes(title: str, override: Optional[int]) -> int:
    """Kept for backward-compat; uses heuristic only."""
    return _estimate_minutes_rule(title, override)

def breakdown(task_title: str,
              breakdown_needed: bool,
              override: Optional[int],
              notes: Optional[str] = None) -> List[Subtask]:
    """
    Prefer Gemini; fallback to rules.
    - task_title: Notion 'Task' title
    - breakdown_needed: your 'Breakdown Needed?' checkbox
    - override: Notion 'Estimated mins' if present
    - notes: Notion 'Notes' rich_text (plain text), optional
    """
    return _call_gemini(task_title, breakdown_needed, override, notes=notes)
