import os
import json
import requests
from dotenv import load_dotenv
from datetime import datetime
import time
from urllib.parse import urlencode
import pytz
from pydub import AudioSegment
import math



# Load environment variables
load_dotenv(".env.local")

# IRS Logics
IRSLOGICS_API_KEY = os.getenv("IRSLOGICS_API_KEY")
IRSLOGICS_UPLOAD_URL = "https://choice.irslogics.com/publicapi/documents/casedocument"

# RingCentral
CLIENT_ID = os.getenv("RINGCENTRAL_CLIENT_ID")
CLIENT_SECRET = os.getenv("RINGCENTRAL_CLIENT_SECRET")
REFRESH_TOKEN = os.getenv("RINGCENTRAL_REFRESH_TOKEN")
BASE_URL = os.getenv("RINGCENTRAL_BASE_URL", "https://platform.ringcentral.com")
TOKEN_URL = f"{BASE_URL}/restapi/oauth/token"

# Input file
MERGED_CALLS_FILE = "ring_central_call_logs_cache/merged_calls_with_case_id_2025-05-05_21-43-15.json"
TEMP_DIR = "temp_recordings"
os.makedirs(TEMP_DIR, exist_ok=True)

MAX_MB = 5.99
MAX_BYTES = MAX_MB * 1024 * 1024  # ~6,285,824 bytes

def split_mp3_if_needed(filepath):
    file_size = os.path.getsize(filepath)
    if file_size <= MAX_BYTES:
        return [filepath]  # No split needed

    print(f"[⚠️] File exceeds {MAX_MB} MB. Splitting...")

    audio = AudioSegment.from_mp3(filepath)
    duration_ms = len(audio)
    num_parts = math.ceil(file_size / MAX_BYTES)
    chunk_length = duration_ms // num_parts

    base_name = os.path.splitext(os.path.basename(filepath))[0]
    dir_name = os.path.dirname(filepath)
    new_files = []

    for i in range(num_parts):
        start = i * chunk_length
        end = None if i == num_parts - 1 else (i + 1) * chunk_length
        chunk = audio[start:end]
        new_filename = os.path.join(dir_name, f"{base_name}_part{i+1}.mp3")
        chunk.export(new_filename, format="mp3")
        new_files.append(new_filename)
        print(f"[🎧] Created: {new_filename}")

    # Optionally delete original large file
    os.remove(filepath)
    return new_files


def get_access_token_from_refresh_token():
    print("[🔄] Exchanging refresh token for access token...")
    data = {
        "grant_type": "refresh_token",
        "refresh_token": REFRESH_TOKEN
    }

    auth = (CLIENT_ID, CLIENT_SECRET)
    response = requests.post(TOKEN_URL, data=data, auth=auth)

    # Debug output
    if response.status_code != 200:
        print("❌ Error response from RingCentral:")
        print("Status Code:", response.status_code)
        print("Response:", response.text)
        response.raise_for_status()

    token_data = response.json()
    access_token = token_data["access_token"]

    # If a new refresh token is returned, save it
    if "refresh_token" in token_data:
        update_refresh_token_env(token_data["refresh_token"])

    print("[✅] Got access token.")
    return access_token


def update_refresh_token_env(new_token, env_path=".env.local"):
    print("[💾] Updating .env.local with new refresh token...")
    lines = []
    updated = False

    # Read existing lines
    with open(env_path, "r") as f:
        for line in f:
            if line.startswith("RINGCENTRAL_REFRESH_TOKEN="):
                lines.append(f"RINGCENTRAL_REFRESH_TOKEN={new_token}\n")
                updated = True
            else:
                lines.append(line)

    # If token wasn't found, append it
    if not updated:
        lines.append(f"RINGCENTRAL_REFRESH_TOKEN={new_token}\n")

    # Write back the updated content
    with open(env_path, "w") as f:
        f.writelines(lines)

    print("[✅] .env.local updated.")


def format_filename(start_time_str):
    try:
        # Convert UTC startTime to Pacific Time
        utc_dt = datetime.strptime(start_time_str, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=pytz.utc)
        pacific_dt = utc_dt.astimezone(pytz.timezone("US/Pacific"))
        timestamp = pacific_dt.strftime("%Y-%m-%d %I-%M-%S %p PDT")
    except Exception as e:
        print(f"[⚠️] Error parsing startTime: {e}")
        timestamp = "unknown_time"

    return f"{TEMP_DIR}/call_{timestamp}.mp3"

def download_recording(recording_uri, access_token, filename):
    headers = {"Authorization": f"Bearer {access_token}"}
    try:
        with requests.get(recording_uri, headers=headers, stream=True) as response:
            response.raise_for_status()
            with open(filename, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
        print(f"[⬇️] Downloaded to {filename}")
        return True
    except Exception as e:
        print(f"[❌] Failed to download recording: {e}")
        return False


def upload_to_irslogics(case_id, file_path):
    print(f"[⬆️] Uploading {file_path} to IRS Logics for CaseID {case_id}...")

    try:
        # Required query parameters
        params = {
            "apikey": IRSLOGICS_API_KEY,
            "CaseID": str(case_id)
        }

        # Construct final URL with params
        full_url = f"{IRSLOGICS_UPLOAD_URL}?{urlencode(params)}"

        with open(file_path, "rb") as f:
            files = {
                "file": (os.path.basename(file_path), f, "audio/mpeg")
            }

            # Send the POST request
            response = requests.post(full_url, files=files)

            print(f"[📬] Status: {response.status_code}")
            print(f"[📩] Response: {response.text}")
            return response.status_code == 200 and "success" in response.text.lower()

    except Exception as e:
        print(f"[❌] Upload error: {e}")
        return False


def main():
    access_token = get_access_token_from_refresh_token()

    # Load matched calls
    with open(MERGED_CALLS_FILE, "r") as f:
        call_logs = json.load(f)

    success_count = 0

    for i, call in enumerate(call_logs, start=1):
        call_id = call["call_id"]
        case_id = call["CaseID"]
        recording_uri = call["recording_uri"]
        start_time = call.get("startTime")
        filename = format_filename(start_time)

        print(f"\n[{i}/{len(call_logs)}] Processing call {call_id} for CaseID {case_id}")

        # Download
        if not download_recording(recording_uri, access_token, filename):
            continue

        # 🔄 Split if file > 5.99MB
        file_list = split_mp3_if_needed(filename)

        # Upload each (split or not)
        for f in file_list:
            if upload_to_irslogics(case_id, f):
                success_count += 1
            else:
                print(f"[❌] Failed to upload {f}")

            # Cleanup
            if os.path.exists(f):
                os.remove(f)

        time.sleep(1)  # Optional: throttle requests slightly

    print(f"\n[✅] Upload complete. Successful uploads: {success_count}/{len(call_logs)}")


if __name__ == "__main__":
    main()
