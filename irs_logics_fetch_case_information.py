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


load_dotenv(".env.local")

API_KEY = os.getenv("IRSLOGICS_API_KEY")
CASE_CACHE_ID_PATH = get_latest_json_file("irs_logics_case_ids_cache")
GET_CASE_URL = "https://choice.irslogics.com/publicapi/2020-02-22/cases/caseinfo"

def fetch_and_cache_irs_logics_cases():
    """
    Fetches case info from IRS Logics based on cached CaseIDs.
    Filters down to fields relevant for phone number matching.
    Saves to a single JSON file and returns the file path.
    """
    if not os.path.exists(CASE_CACHE_ID_PATH):
        raise FileNotFoundError(f"Missing cache file: {CASE_CACHE_ID_PATH}")

    with open(CASE_CACHE_ID_PATH, "r") as f:
        cache = json.load(f)

    all_status_ids = list(cache.keys())
    results = []

    for status_id in all_status_ids:
        case_ids = cache[status_id]
        print(f"\n[🔁] StatusID: {status_id} — Total Cases: {len(case_ids)}")

        for i, case_id in enumerate(case_ids):
            print(f"📁 Case #{i+1} — CaseID: {case_id}")
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

            except Exception as e:
                print(f"❌ Error fetching CaseID {case_id}: {e}")

    # Save results
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"all_cases_with_numbers_{timestamp}.json"
    output_path = os.path.join("irs_logics_case_info_cache", filename)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\n✅ Saved {len(results)} case contact entries to {output_path}")
    return output_path

# Optional: allow standalone usage
if __name__ == "__main__":
    fetch_and_cache_irs_logics_cases()
