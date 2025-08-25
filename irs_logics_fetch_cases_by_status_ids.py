import os
import json
import requests
from time import sleep
from dotenv import load_dotenv
from datetime import datetime
from utilities import get_latest_json_file
import logging
import sys

# ✅ Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)



def fetch_and_cache_case_ids() -> str:
    """
    Fetches all case IDs from IRS Logics grouped by StatusID.
    Saves them to a timestamped JSON in irs_logics_case_ids_cache.
    Returns the output file path.
    """
    # Load from .env.local if present (for local dev), otherwise Azure will use Function App settings
    if os.path.exists(".env.local"):
        load_dotenv(".env.local")
    API_KEY = os.getenv("IRSLOGICS_API_KEY")
    STATUS_FILE = "irs_logics_status_id.json"
    OUTPUT_DIR = "irs_logics_case_ids_cache"
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    OUTPUT_FILE = os.path.join(OUTPUT_DIR, f"all_case_ids_{timestamp}.json")

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Load previous case cache if available
    try:
        prev_file = get_latest_json_file(OUTPUT_DIR)
        with open(prev_file, "r") as f:
            previous_cache = json.load(f)
    except Exception:
        previous_cache = {}

    with open(STATUS_FILE, "r") as f:
        statuses = json.load(f)

    BASE_URL = "https://choice.irslogics.com/publicapi/2020-02-22/cases/GetCasesByStatus"
    case_cache = {}

    for entry in statuses:
        status_id = str(entry["StatusID"])
        status_name = entry["StatusName"]

        # Skip if previously cached and assume unchanged
        prev_ids = previous_cache.get(status_id, [])
        logger.info(f"[🔍] Checking {status_name} (StatusID: {status_id})")

        try:
            params = {
                "apikey": API_KEY,
                "StatusID": status_id
            }
            response = requests.get(BASE_URL, params=params)
            response.raise_for_status()
            data = response.json()

            if data["status"] == "success":
                current_ids = data.get("data", [])

                if set(current_ids) == set(prev_ids):
                    logger.info(f"[⏩] Skipped — no change from previous cache.")
                    case_cache[status_id] = prev_ids  # use previous
                    continue

                logger.info(f"[✅] Found {len(current_ids)} case IDs (updated).")
                case_cache[status_id] = current_ids
            else:
                logger.info(f"[⚠️] Failed response: {data.get('message')}")
                case_cache[status_id] = prev_ids  # fallback to previous

        except Exception as e:
            logger.info(f"[❌] Error fetching StatusID {status_id}: {e}")
            case_cache[status_id] = prev_ids  # fallback to previous

        sleep(1)

    with open(OUTPUT_FILE, "w") as f:
        json.dump(case_cache, f, indent=2)

    logger.info(f"[💾] Case cache saved to: {OUTPUT_FILE}")
    return OUTPUT_FILE


if __name__ == "__main__":
    fetch_and_cache_case_ids()
