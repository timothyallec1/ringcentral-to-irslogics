import os
import json
import requests
from time import sleep
from dotenv import load_dotenv
from datetime import datetime


def fetch_and_cache_case_ids() -> str:
    """
    Fetches all case IDs from IRS Logics grouped by StatusID.
    Saves them to a timestamped JSON in irs_logics_case_ids_cache.
    Returns the output file path.
    """
    load_dotenv(".env.local")
    API_KEY = os.getenv("IRSLOGICS_API_KEY")
    STATUS_FILE = "irs_logics_status_id.json"
    OUTPUT_DIR = "irs_logics_case_ids_cache"
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    OUTPUT_FILE = os.path.join(OUTPUT_DIR, f"all_case_ids_{timestamp}.json")

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    with open(STATUS_FILE, "r") as f:
        statuses = json.load(f)

    BASE_URL = "https://choice.irslogics.com/publicapi/2020-02-22/cases/GetCasesByStatus"
    case_cache = {}

    for entry in statuses:
        status_id = entry["StatusID"]
        status_name = entry["StatusName"]

        print(f"[🔍] Fetching CaseIDs for: {status_name} (StatusID: {status_id})")

        try:
            params = {
                "apikey": API_KEY,
                "StatusID": status_id
            }
            response = requests.get(BASE_URL, params=params)
            response.raise_for_status()
            data = response.json()

            if data["status"] == "success":
                case_ids = data.get("data", [])
                print(f"[✅] Found {len(case_ids)} case IDs.")
                case_cache[str(status_id)] = case_ids
            else:
                print(f"[⚠️] Failed response: {data.get('message')}")

        except Exception as e:
            print(f"[❌] Error fetching StatusID {status_id}: {e}")

        sleep(1)

    with open(OUTPUT_FILE, "w") as f:
        json.dump(case_cache, f, indent=2)

    print(f"[💾] Rebuilt case cache and saved to: {OUTPUT_FILE}")
    return OUTPUT_FILE


if __name__ == "__main__":
    fetch_and_cache_case_ids()
