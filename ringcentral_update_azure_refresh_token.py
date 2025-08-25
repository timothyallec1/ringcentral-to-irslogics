# --------------------------------------------------------------------
# Script: ringcentral_update_refresh_token.py
# Description:
#   Utility functions to persist and retrieve the RingCentral
#   refresh token in /home/refresh_token.txt (Azure persistent storage).
#
#   - Local: prefer .env.local, fallback to /home/refresh_token.txt, then env var
#   - Azure: prefer /home/refresh_token.txt, fallback to env var
#   - Always overwrite with the latest refresh token
# --------------------------------------------------------------------

import os
from dotenv import load_dotenv
import logging
import sys

# ✅ Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)


REFRESH_TOKEN_FILE = "/home/refresh_token.txt"

def load_refresh_token() -> str:
    """
    Reads the current refresh token with correct local vs Azure precedence:
      - Local dev: prefer .env.local
      - Azure: prefer /home/refresh_token.txt
      - Both: fallback to env var
    """
    # Local development
    if os.path.exists(".env.local"):
        load_dotenv(".env.local", override=True)
        token = os.getenv("RINGCENTRAL_REFRESH_TOKEN")
        if token:
            logger.info("[🔑] Loaded refresh token from .env.local")
            return token

    # Azure or fallback
    if os.path.exists(REFRESH_TOKEN_FILE):
        with open(REFRESH_TOKEN_FILE, "r") as f:
            token = f.read().strip()
        if token:
            logger.info(f"[🔑] Loaded refresh token from {REFRESH_TOKEN_FILE}")
            return token

    # Environment fallback
    token = os.getenv("RINGCENTRAL_REFRESH_TOKEN")
    if token:
        logger.info("[🔑] Loaded refresh token from environment variable")
        return token

    raise RuntimeError("❌ No refresh token found in .env.local, file, or environment.")


def save_refresh_token(new_token: str):
    """
    Saves the given refresh token into:
      - /home/refresh_token.txt (Azure)
      - .env.local (if present, for local dev)
    """
    # Always update Azure persistent file
    os.makedirs(os.path.dirname(REFRESH_TOKEN_FILE), exist_ok=True)
    with open(REFRESH_TOKEN_FILE, "w") as f:
        f.write(new_token)
    logger.info(f"[💾] Refresh token updated in {REFRESH_TOKEN_FILE}")

    # Update .env.local if running locally
    if os.path.exists(".env.local"):
        try:
            updated = False
            lines = []
            with open(".env.local", "r") as f:
                for line in f:
                    if line.startswith("RINGCENTRAL_REFRESH_TOKEN="):
                        lines.append(f"RINGCENTRAL_REFRESH_TOKEN={new_token}\n")
                        updated = True
                    else:
                        lines.append(line)

            if not updated:
                lines.append(f"RINGCENTRAL_REFRESH_TOKEN={new_token}\n")

            with open(".env.local", "w") as f:
                f.writelines(lines)

            logger.info("[💾] Refresh token updated in .env.local")
        except Exception as e:
            logger.info(f"[⚠️] Failed to update .env.local: {e}")
