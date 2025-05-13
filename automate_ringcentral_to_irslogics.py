import os

from ring_central_fetch_calls import fetch_and_cache_ringcentral_calls
from irs_logics_fetch_case_information import fetch_and_cache_irs_logics_cases
from irs_logics_match_caseID_with_call_logs import match_calls_to_cases
from utilities import get_latest_json_file




def automate_ringcentral_to_irslogics():
    print("📞 Step 1: Fetching RingCentral call logs...")
    fetch_and_cache_ringcentral_calls()
    call_log_path = get_latest_json_file("ring_central_call_logs_cache")
    print(f"✅ Latest call log: {call_log_path}\n")

    print("📂 Step 2: Fetching IRS Logics cases...")
    fetch_and_cache_irs_logics_cases()
    case_log_path = get_latest_json_file("irs_logics_case_info_cache")
    print(f"✅ Latest IRS Logics case file: {case_log_path}\n")

    print("🔗 Step 3: Matching calls to IRS Logics cases...")
    matched_path, unmatched_path = match_calls_to_cases(call_log_path, case_log_path)
    print(f"✅ Merged file: {matched_path}")
    print(f"⚠️  Unmatched file: {unmatched_path}")


if __name__ == "__main__":
    automate_ringcentral_to_irslogics()
