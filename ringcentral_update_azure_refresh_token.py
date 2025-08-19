# --------------------------------------------------------------------
# Script: ring_central_update_refresh_token.py
# Description:
#   Utility functions to persist and retrieve the RingCentral
#   refresh token in /home/refresh_token.txt (Azure persistent storage).
#
#   - Local & Azure both use /home/refresh_token.txt
#   - Always overwrite with the latest refresh token
# --------------------------------------------------------------------

import os

REFRESH_TOKEN_FILE = "/home/refresh_token.txt"

def load_refresh_token() -> str:
    """
    Reads the current refresh token from /home/refresh_token.txt.
    Falls back to environment variable if the file doesn't exist.
    """
    try:
        with open(REFRESH_TOKEN_FILE, "r") as f:
            token = f.read().strip()
            print(f"[🔑] Loaded refresh token from {REFRESH_TOKEN_FILE}")
            return token
    except FileNotFoundError:
        env_token = os.getenv("RINGCENTRAL_REFRESH_TOKEN")
        if not env_token:
            raise RuntimeError("❌ No refresh token found in file or environment.")
        print("[⚠️] refresh_token.txt not found. Using env var instead.")
        return env_token

def save_refresh_token(new_token: str):
    """
    Saves the given refresh token into /home/refresh_token.txt.
    Overwrites any existing value.
    """
    os.makedirs(os.path.dirname(REFRESH_TOKEN_FILE), exist_ok=True)
    with open(REFRESH_TOKEN_FILE, "w") as f:
        f.write(new_token)
    print(f"[💾] Refresh token updated in {REFRESH_TOKEN_FILE}")
