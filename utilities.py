# utilities.py

import os

def get_latest_json_file(directory: str) -> str:
    """
    Returns the full path to the most recently modified JSON file in the given directory.
    """
    if not os.path.exists(directory):
        raise FileNotFoundError(f"Directory does not exist: {directory}")

    files = [f for f in os.listdir(directory) if f.endswith(".json")]
    if not files:
        raise FileNotFoundError(f"No JSON files found in: {directory}")

    files = [os.path.join(directory, f) for f in files]
    latest_file = max(files, key=os.path.getmtime)
    return latest_file
