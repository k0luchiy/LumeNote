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

def set_user_state(user_id: int, project: Optional[str] = None, lang: Optional[str] = None, main_topic: Optional[str] = None): # <-- Add main_topic
    with lock:
        states = _load_states()
        user_id_str = str(user_id)
        if user_id_str not in states:
            states[user_id_str] = {"active_project": "default", "language": "en", "main_topic": None}

        if project is not None:
            states[user_id_str]["active_project"] = project
        if lang is not None:
            states[user_id_str]["language"] = lang
        # ADD THIS BLOCK
        if main_topic is not None:
            states[user_id_str]["main_topic"] = main_topic

        _save_states(states)

def get_user_projects(user_id: int) -> list:
    """
    Gets a list of ALL full collection names for a given user.
    e.g., ['user_123_project-a', 'user_123_project-b']
    """
    from tele_notebook.services.rag_service import client
    try:
        collections = client.list_collections()
        user_prefix = f"user_{user_id}_"
        # --- THIS IS THE FIX ---
        # Return the full collection name, not the shortened version
        return [col.name for col in collections if col.name.startswith(user_prefix)]
    except Exception:
        return []

# --- ADD A NEW FUNCTION FOR DISPLAY ---
def get_user_display_projects(user_id: int) -> list:
    """
    Gets a list of user-friendly project names for display.
    e.g., ['project-a', 'project-b']
    """
    full_names = get_user_projects(user_id)
    user_prefix = f"user_{user_id}_"
    return [name.replace(user_prefix, "", 1) for name in full_names]