import os
import json
import requests
from dotenv import load_dotenv

# Load API key
load_dotenv(".env.local")
API_KEY = os.getenv("IRSLOGICS_API_KEY")
CASE_CACHE_PATH = "irs_logics_case_logs_cache/cached_case_ids.json"
GET_CASE_URL = "https://choice.irslogics.com/publicapi/2020-02-22/cases/caseinfo"

# Load cached case IDs
with open(CASE_CACHE_PATH, "r") as f:
    cache = json.load(f)

all_status_ids = list(cache.keys())

# Container for results
results = []

# Loop through first 5 StatusIDs
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

# Save results to JSON for review
output_path = "irs_logics_case_logs_cache/all_cases_with_numbers.json"
with open(output_path, "w") as f:
    json.dump(results, f, indent=2)

print(f"\n✅ Saved {len(results)} case contact entries from first 5 StatusIDs to {output_path}")
