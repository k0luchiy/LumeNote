import json
import os
from filelock import FileLock
from typing import Dict, Optional

"""
Manages user-specific data like active project and language. 
We'll use a simple JSON file with a file lock to ensure it's 
process-safe between the bot and workers.
"""

STATE_FILE = "user_states.json"
lock = FileLock(f"{STATE_FILE}.lock")

def _load_states() -> Dict:
    if not os.path.exists(STATE_FILE):
        return {}
    with open(STATE_FILE, "r") as f:
        # Handle empty file case
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}

def _save_states(states: Dict):
    with open(STATE_FILE, "w") as f:
        json.dump(states, f, indent=2)

def get_user_state(user_id: int) -> Dict:
    with lock:
        states = _load_states()
        return states.get(str(user_id), {"active_project": "default", "language": "en"})

def set_user_state(user_id: int, project: Optional[str] = None, lang: Optional[str] = None):
    with lock:
        states = _load_states()
        user_id_str = str(user_id)
        if user_id_str not in states:
            states[user_id_str] = {"active_project": "default", "language": "en"}

        if project is not None:
            states[user_id_str]["active_project"] = project
        if lang is not None:
            states[user_id_str]["language"] = lang

        _save_states(states)

def get_user_projects(user_id: int) -> list:
    # This is a simplified approach for the MVP.
    from tele_notebook.services.rag_service import client
    try:
        collections = client.list_collections()
        user_prefix = f"user_{user_id}_"
        return [col.name.replace(user_prefix, "", 1) for col in collections if col.name.startswith(user_prefix)]
    except Exception:
        # ChromaDB might not be initialized on the very first run
        return []