from ring_central_fetch_calls import fetch_and_cache_ringcentral_calls

def main():
    print("📞 Step 1: Fetching and saving RingCentral call logs with recordings...")
    try:
        calls_json_path = fetch_and_cache_ringcentral_calls()
        print(f"✅ Call logs saved to: {calls_json_path}\n")
    except Exception as e:
        print("❌ Error during RingCentral call fetch:", e)
        return

    # TODO: Next step – match with IRS Logics cases
