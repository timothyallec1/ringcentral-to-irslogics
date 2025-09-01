import os

from ring_central_fetch_calls import fetch_and_cache_ringcentral_calls
from irs_logics_fetch_cases_by_status_ids import fetch_and_cache_case_ids
from irs_logics_fetch_case_information import fetch_and_cache_irs_logics_cases
from irs_logics_match_caseID_with_call_logs import match_calls_to_cases
from irs_logics_upload_call_recordings import upload_call_recordings_to_irslogics
from storage_utils import load_latest_json, save_json   # ✅ use our new helper


def automate_ringcentral_to_irslogics():
    print("📞 Step 1: Fetching RingCentral call logs...")
    call_log_path = fetch_and_cache_ringcentral_calls()   # ✅ returns local path OR blob name
    print(f"✅ Latest call log: {call_log_path}\n")

    print("📄 Step 2: Fetching IRS Logics case IDs by StatusID...")
    fetch_and_cache_case_ids()
    print("✅ Case ID cache rebuilt.\n")

    print("📂 Step 3: Fetching IRS Logics case information (phone numbers)...")
    case_log_path = fetch_and_cache_irs_logics_cases()    # ✅ should return path/blob like we did above
    print(f"✅ Latest IRS Logics case file: {case_log_path}\n")

    print("🔗 Step 4: Matching calls to IRS Logics cases...")
    # Instead of relying on get_latest_json_file, just pass the paths/blobs we already have
    matched_path, unmatched_path = match_calls_to_cases(call_log_path, case_log_path)
    print(f"✅ Merged file: {matched_path}")
    print(f"⚠️  Unmatched file: {unmatched_path}\n")

    print("⬆️ Step 5: Uploading call recordings to IRS Logics...")
    upload_call_recordings_to_irslogics()
    print("✅ Upload step completed.")


if __name__ == "__main__":
    automate_ringcentral_to_irslogics()
    print("\n🎉 All steps completed successfully!")