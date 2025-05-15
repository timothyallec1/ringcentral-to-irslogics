# ---------------------------------------------------------------
# Script: irs_logics_fetch_cases.py
# Date Created: 2025-05-06
# Description: 
#   Fetches detailed case information from the IRS Logics API 
#   using cached case IDs grouped by StatusID. Extracts relevant 
#   contact fields (CaseID, Name, CellPhone, HomePhone, WorkPhone) 
#   and saves the result to a JSON file for downstream matching.
#
# Output:
#   - irs_logics_case_logs_cache/all_cases_with_numbers.json
#     (List of case contacts with phone numbers)
# ---------------------------------------------------------------

# irs_logics_fetch_cases.py

import os
import json
import requests
from dotenv import load_dotenv
from datetime import datetime
from utilities import get_latest_json_file
from time import sleep


# load_dotenv(".env.local")

# API_KEY = os.getenv("IRSLOGICS_API_KEY")
# CASE_CACHE_ID_PATH = get_latest_json_file("irs_logics_case_ids_cache")
# GET_CASE_URL = "https://choice.irslogics.com/publicapi/2020-02-22/cases/caseinfo"

# force refresh flag set it to true if you want case info to be fetched again for all cases
def fetch_and_cache_irs_logics_cases(force_refresh: bool = False):
    load_dotenv(".env.local")
    API_KEY = os.getenv("IRSLOGICS_API_KEY")
    CASE_CACHE_ID_PATH = get_latest_json_file("irs_logics_case_ids_cache")
    GET_CASE_URL = "https://choice.irslogics.com/publicapi/2020-02-22/cases/caseinfo"
    OUTPUT_DIR = "irs_logics_case_info_cache"
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    output_path = os.path.join(OUTPUT_DIR, f"all_cases_with_numbers_{timestamp}.json")
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Load previous case info if available and not forcing refresh
    prev_cases_by_id = {}
    if not force_refresh:
        try:
            previous_log = get_latest_json_file(OUTPUT_DIR)
            with open(previous_log, "r") as f:
                previous_entries = json.load(f)
                prev_cases_by_id = {str(entry["CaseID"]): entry for entry in previous_entries}
        except Exception:
            pass  # no previous cache found

    if not os.path.exists(CASE_CACHE_ID_PATH):
        raise FileNotFoundError(f"Missing cache file: {CASE_CACHE_ID_PATH}")

    with open(CASE_CACHE_ID_PATH, "r") as f:
        cache = json.load(f)

    results = []
    skipped = 0
    fetched = 0

    for status_id, case_ids in cache.items():
        print(f"\n[🔁] StatusID: {status_id} — Total Cases: {len(case_ids)}")

        for i, case_id in enumerate(case_ids):
            str_case_id = str(case_id)

            if not force_refresh and str_case_id in prev_cases_by_id:
                results.append(prev_cases_by_id[str_case_id])
                skipped += 1
                continue

            print(f"📁 Fetching Case #{i+1} — CaseID: {case_id}")
            try:
                response = requests.get(GET_CASE_URL, params={
                    "apikey": API_KEY,
                    "CaseID": case_id
                })
                response.raise_for_status()
                data = response.json()

                if data.get("status") != "success":
                    print(f"❌ Failed to retrieve case: {data.get('message')}")
                    continue

                case = data["data"]
                result = {
                    "CaseID": case.get("CaseID"),
                    "Name": f"{case.get('FirstName', '')} {case.get('LastName', '')}".strip(),
                    "CellPhone": case.get("CellPhone"),
                    "HomePhone": case.get("HomePhone"),
                    "WorkPhone": case.get("WorkPhone")
                }
                results.append(result)
                fetched += 1

            except Exception as e:
                print(f"❌ Error fetching CaseID {case_id}: {e}")

            sleep(0.3)

    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\n✅ Saved {len(results)} case contact entries to {output_path}")
    print(f"⏩ Skipped from cache: {skipped} | 🌐 Fetched from API: {fetched}")
    return output_path


# Optional: allow standalone usage
if __name__ == "__main__":
    fetch_and_cache_irs_logics_cases()
