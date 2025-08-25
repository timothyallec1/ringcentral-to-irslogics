import os

from ring_central_fetch_calls import fetch_and_cache_ringcentral_calls
from irs_logics_fetch_cases_by_status_ids import fetch_and_cache_case_ids
from irs_logics_fetch_case_information import fetch_and_cache_irs_logics_cases
from irs_logics_match_caseID_with_call_logs import match_calls_to_cases
from irs_logics_upload_call_recordings import upload_call_recordings_to_irslogics
from storage_utils import load_latest_json   # ✅ use our new helper
import logging
import sys

# ✅ Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)



def automate_ringcentral_to_irslogics():
    logger.info("📞 Step 1: Fetching RingCentral call logs...")
    call_log_path = fetch_and_cache_ringcentral_calls()   # ✅ returns local path OR blob name
    logger.info(f"✅ Latest call log: {call_log_path}\n")

    logger.info("📄 Step 2: Fetching IRS Logics case IDs by StatusID...")
    fetch_and_cache_case_ids()
    logger.info("✅ Case ID cache rebuilt.\n")

    logger.info("📂 Step 3: Fetching IRS Logics case information (phone numbers)...")
    case_log_path = fetch_and_cache_irs_logics_cases()    # ✅ should return path/blob like we did above
    logger.info(f"✅ Latest IRS Logics case file: {case_log_path}\n")

    logger.info("🔗 Step 4: Matching calls to IRS Logics cases...")
    # Instead of relying on get_latest_json_file, just pass the paths/blobs we already have
    matched_path, unmatched_path = match_calls_to_cases(call_log_path, case_log_path)
    logger.info(f"✅ Merged file: {matched_path}")
    logger.info(f"⚠️  Unmatched file: {unmatched_path}\n")

    logger.info("⬆️ Step 5: Uploading call recordings to IRS Logics...")
    upload_call_recordings_to_irslogics()
    logger.info("✅ Upload step completed.")


if __name__ == "__main__":
    automate_ringcentral_to_irslogics()
    logger.info("\n🎉 All steps completed successfully!")