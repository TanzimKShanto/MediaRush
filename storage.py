import json
import os

JSON_FILE = "data.json"


def load_data():
    """Load message IDs from a JSON file."""
    if not os.path.exists(JSON_FILE):
        return {}  # Return an empty dictionary if the file doesn't exist
    with open(JSON_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}  # Return an empty dictionary if the JSON file is empty or corrupt


async def save_data(data, lock):
    """Save message IDs to a JSON file."""
    async with lock:
        with open(JSON_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
