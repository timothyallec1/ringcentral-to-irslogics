from ring_central_fetch_calls import fetch_and_cache_ringcentral_calls
from irs_logics_fetch_cases import fetch_and_cache_irs_logics_cases

def automate_ringcentral_to_irslogics():
    print("📞 Step 1: Fetching RingCentral call logs...")
    call_log_path = fetch_and_cache_ringcentral_calls()
    print(f"✅ Call logs saved to: {call_log_path}\n")

    print("📂 Step 2: Fetching IRS Logics cases...")
    case_log_path = fetch_and_cache_irs_logics_cases()
    print(f"✅ IRS Logics cases saved to: {case_log_path}\n")

    # TODO: Match calls to cases...

if __name__ == "__main__":
    automate_ringcentral_to_irslogics()
