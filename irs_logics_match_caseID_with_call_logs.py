# ---------------------------------------------------------------
# Script: irs_logics_match_caseID_with_call_logs.py
# Date Created: 2025-05-06
# Description:
#   This script matches RingCentral call logs with IRS Logics cases 
#   by comparing phone numbers. If a match is found based on any of 
#   the phone fields (CellPhone, HomePhone, WorkPhone), the call is 
#   enriched with the corresponding CaseID and contact name.
#
#   Features:
#   - Loads call log JSON and case contact JSON files
#   - Matches call log entries with IRS Logics cases using phone numbers
#   - Outputs two JSON files:
#       1. Merged call logs with matching CaseIDs
#       2. Unmatched call logs for auditing
#
#   Input:
#     - CALLS_FILE: A JSON file containing RingCentral call logs
#     - CASES_FILE: A JSON file containing case contact details with phone numbers
#
#   Output:
#     - merged_calls_with_case_id_<timestamp>.json
#     - unmatched_calls_<timestamp>.json
#
# ---------------------------------------------------------------


import json
import os
from datetime import datetime

# File paths
CALLS_FILE = "ring_central_call_logs_cache/calls_2025-05-05_2032.json"
CASES_FILE = "irs_logics_case_logs_cache/all_cases_with_numbers.json"
timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
OUTPUT_FILE = f"irs_matched_calls_cache/merged_calls_with_case_id_{timestamp}.json"
UNMATCHED_FILE = f"irs_unmatched_calls_cache/unmatched_calls_{timestamp}.json"

# Load call logs
with open(CALLS_FILE, "r") as f:
    call_logs = json.load(f)

# Load IRS Logics case contacts
with open(CASES_FILE, "r") as f:
    cases = json.load(f)

# Index case contacts by all known phone numbers
phone_to_case = {}
for case in cases:
    for phone_field in ["CellPhone", "HomePhone", "WorkPhone"]:
        phone = case.get(phone_field)
        if phone:
            phone_to_case[phone] = {
                "CaseID": case["CaseID"],
                "Name": case["Name"]
            }

# Match calls to cases
matched_calls = []
unmatched_calls = []

for call in call_logs:
    phone = call.get("client_number")
    if phone and phone in phone_to_case:
        matched = call.copy()
        matched.update(phone_to_case[phone])
        matched_calls.append(matched)
    else:
        unmatched_calls.append(call)

# Create output directory if it doesn't exist
os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)

# Save matched calls
with open(OUTPUT_FILE, "w") as f:
    json.dump(matched_calls, f, indent=2)

# Save unmatched calls
with open(UNMATCHED_FILE, "w") as f:
    json.dump(unmatched_calls, f, indent=2)

# Log results
print(f"[✅] Matched {len(matched_calls)} calls saved to {OUTPUT_FILE}")
print(f"[⚠️] Unmatched {len(unmatched_calls)} calls saved to {UNMATCHED_FILE}")
