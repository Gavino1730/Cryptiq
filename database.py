"""
database.py - Handles all persistent data storage and retrieval for Cryptiq bot.
"""
import os
import json
from typing import Any, Dict, Union

USER_DATA_FILE = os.path.join(os.path.dirname(__file__), "user_data.json")
CHAT_LOG_FILE = os.path.join(os.path.dirname(__file__), "chat_log.json")
ALERTS_FILE = os.path.join(os.path.dirname(__file__), "alerts.json")


def load_user_data(user_id: Union[str, int]) -> Dict[str, Any]:
    """Load user data for a given user ID."""
    try:
        with open(USER_DATA_FILE, "r") as f:
            data: Dict[str, Any] = json.load(f)
        return data["users"].get(str(user_id), {})
    except Exception:
        return {}


def save_user_data(user_id: Union[str, int], user_data: Dict[str, Any]) -> None:
    """Save user data for a given user ID."""
    try:
        with open(USER_DATA_FILE, "r") as f:
            data = json.load(f)
    except Exception:
        data = {"users": {}}
    data["users"][str(user_id)] = user_data
    with open(USER_DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)


def load_alerts() -> Dict[str, Any]:
    """Load all alerts from storage."""
    try:
        with open(ALERTS_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {}


def save_alerts(alerts: Dict[str, Any]) -> None:
    """Save all alerts to storage."""
    with open(ALERTS_FILE, "w") as f:
        json.dump(alerts, f, indent=2)


def log_chat(user_id: Union[str, int], user_message: str, bot_response: str, portfolio_value: Union[float, None] = None) -> None:
    """Log a chat message and bot response for a user."""
    import datetime
    import pytz
    pacific = pytz.timezone('US/Pacific')
    now = datetime.datetime.now(pacific)
    now_str = now.strftime('%Y-%m-%d %I:%M %p %Z')
    if os.path.exists(CHAT_LOG_FILE):
        with open(CHAT_LOG_FILE, "r") as f:
            data = json.load(f)
    else:
        data = {"logs": {}}
    uid = str(user_id)
    if uid not in data["logs"]:
        data["logs"][uid] = []
    entry: Dict[str, Any] = {
        "timestamp": now_str,
        "user_message": user_message,
        "bot_response": bot_response
    }
    if portfolio_value is not None:
        entry["portfolio_value"] = portfolio_value
    data["logs"][uid].append(entry)
    with open(CHAT_LOG_FILE, "w") as f:
        json.dump(data, f, indent=2)
