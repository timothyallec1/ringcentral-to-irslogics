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

# Step 1: Get first status ID and associated case IDs
first_status_id = next(iter(cache))
case_ids = cache[first_status_id]
print(f"[🔍] Matching cases for StatusID {first_status_id} with {len(case_ids)} case IDs...")

# Step 2: Loop through case IDs
for i, case_id in enumerate(case_ids):
    print(f"\n📁 Case #{i+1} — CaseID: {case_id}")

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
        print(f"  Name: {case.get('FirstName', '')} {case.get('LastName', '')}")
        print(f"  CellPhone: {case.get('CellPhone')}")
        print(f"  HomePhone: {case.get('HomePhone')}")
        print(f"  WorkPhone: {case.get('WorkPhone')}")

    except Exception as e:
        print(f"❌ Error fetching CaseID {case_id}: {e}")

# Optional: add break to only do a few
# if i == 0: break
