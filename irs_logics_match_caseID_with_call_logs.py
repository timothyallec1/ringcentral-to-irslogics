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
from storage_utils import save_json, load_latest_json

def match_calls_to_cases(calls_file: str, cases_file: str) -> tuple[str, str]:
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    matched_filename = f"merged_calls_with_case_id_{timestamp}.json"
    unmatched_filename = f"unmatched_calls_{timestamp}.json"

    # Load calls
    if calls_file:
        try:
            with open(calls_file, "r") as f:
                call_logs = json.load(f)
        except FileNotFoundError:
            # Fallback to blob
            call_logs = load_latest_json("ring_central_call_logs_cache", "fetchedcallsringcentral")
    else:
        call_logs = load_latest_json("ring_central_call_logs_cache", "fetchedcallsringcentral")

    # Load cases
    if cases_file:
        try:
            with open(cases_file, "r") as f:
                cases = json.load(f)
        except FileNotFoundError:
            cases = load_latest_json("irs_logics_case_info_cache", "caseinfo")
    else:
        cases = load_latest_json("irs_logics_case_info_cache", "caseinfo")

    # Try to load previous matched file to preserve uploaded flags
    try:
        prev_file = get_latest_json_file("irs_matched_calls_cache")
        with open(prev_file, "r") as f:
            prev_matched = json.load(f)
        prev_uploaded = {c["call_id"]: c.get("uploaded", False) for c in prev_matched}
    except Exception:
        prev_uploaded = {}

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

            # Preserve uploaded flag if call_id was seen before
            call_id = matched["call_id"]
            matched["uploaded"] = prev_uploaded.get(call_id, False)

            matched_calls.append(matched)
        else:
            unmatched_calls.append(call)

    matched_blob = save_json(matched_calls, "irs_matched_calls_cache", matched_filename, "matchedcalls")
    unmatched_blob = save_json(unmatched_calls, "irs_unmatched_calls_cache", unmatched_filename, "unmatchedcalls")

    print(f"[✅] Matched {len(matched_calls)} calls saved to {matched_blob}")
    print(f"[⚠️] Unmatched {len(unmatched_calls)} calls saved to {unmatched_blob}")

    return matched_blob, unmatched_blob


# Optional standalone usage
if __name__ == "__main__":
    latest_calls = get_latest_json_file("ring_central_call_logs_cache")
    latest_cases = get_latest_json_file("irs_logics_case_info_cache")
    
    match_calls_to_cases(latest_calls, latest_cases)


