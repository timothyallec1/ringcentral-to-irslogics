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
from utilities import get_latest_json_file

def match_calls_to_cases(calls_file: str, cases_file: str) -> tuple[str, str]:
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    output_file = f"irs_matched_calls_cache/merged_calls_with_case_id_{timestamp}.json"
    unmatched_file = f"irs_unmatched_calls_cache/unmatched_calls_{timestamp}.json"


    # Load call logs
    with open(calls_file, "r") as f:
        call_logs = json.load(f)

    # Load IRS Logics case contacts
    with open(cases_file, "r") as f:
        cases = json.load(f)

    # Index by phone number
    phone_to_case = {}
    for case in cases:
        for phone_field in ["CellPhone", "HomePhone", "WorkPhone"]:
            phone = case.get(phone_field)
            if phone:
                phone_to_case[phone] = {
                    "CaseID": case["CaseID"],
                    "Name": case["Name"]
                }

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

    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    os.makedirs(os.path.dirname(unmatched_file), exist_ok=True)

    with open(output_file, "w") as f:
        json.dump(matched_calls, f, indent=2)

    with open(unmatched_file, "w") as f:
        json.dump(unmatched_calls, f, indent=2)

    print(f"[✅] Matched {len(matched_calls)} calls saved to {output_file}")
    print(f"[⚠️] Unmatched {len(unmatched_calls)} calls saved to {unmatched_file}")

    return output_file, unmatched_file

# Optional standalone usage
if __name__ == "__main__":
    latest_calls = get_latest_json_file("ring_central_call_logs_cache")
    latest_cases = get_latest_json_file("irs_logics_case_info_cache")
    
    match_calls_to_cases(latest_calls, latest_cases)


