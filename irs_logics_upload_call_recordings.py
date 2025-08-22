# ---------------------------------------------------------------
# Script: irs_logics_upload_call_recordings.py
# Date Created: 2025-05-06
# Description:
#   Automates the process of uploading RingCentral call recordings 
#   to the IRS Logics platform by matching calls with CaseIDs.
#
#   Features:
#   - Downloads call recordings from RingCentral using a refresh token
#   - Splits recordings larger than 5.99 MB into smaller MP3 parts
#   - Uploads each recording or split part to IRS Logics
#   - Automatically updates the refresh token if a new one is received
#   - Supports retrying failed uploads with recursive splitting
# ---------------------------------------------------------------

import os
import json
import stat
import requests
from dotenv import load_dotenv
from datetime import datetime
import time
from urllib.parse import urlencode
import pytz
import math
import platform
from pydub import AudioSegment
from pydub import utils
from utilities import get_latest_json_file
from ringcentral_update_azure_refresh_token import load_refresh_token, save_refresh_token

# ✅ Handle ffmpeg paths for both Windows (local) and Azure/Linux
# ✅ Handle ffmpeg paths for both Windows (local) and Azure/Linux
ffmpeg_dir = os.path.join(os.getcwd(), "tools", "ffmpeg")
is_windows = platform.system().lower().startswith("win")

if is_windows:
    ffmpeg_path = os.path.join(ffmpeg_dir, "ffmpeg.exe")
    ffprobe_path = os.path.join(ffmpeg_dir, "ffprobe.exe")

    print(f"[DEBUG] PATH updated to include ffmpeg dir: {ffmpeg_dir}")
    print(f"[DEBUG] ffmpeg exists? {os.path.exists(ffmpeg_path)}")
    print(f"[DEBUG] ffprobe exists? {os.path.exists(ffprobe_path)}")

else:
    ffmpeg_path = os.path.join(ffmpeg_dir, "ffmpeg")
    ffprobe_path = os.path.join(ffmpeg_dir, "ffprobe")
    # Ensure executables are +x on Azure/Linux
    for binary in [ffmpeg_path, ffprobe_path]:
        if os.path.exists(binary):
            os.chmod(binary, os.stat(binary).st_mode | stat.S_IEXEC)

# Tell pydub to use the bundled ffmpeg/ffprobe
AudioSegment.converter = ffmpeg_path
AudioSegment.ffprobe = ffprobe_path
utils.get_prober_name = lambda: ffprobe_path
utils.get_encoder_name = lambda: ffmpeg_path

print(f"[🎧] Using ffmpeg at {ffmpeg_path}")
print(f"[🎧] Using ffprobe at {ffprobe_path}")
print(f"[DEBUG] ffmpeg exists? {os.path.exists(ffmpeg_path)}")
print(f"[DEBUG] ffprobe exists? {os.path.exists(ffprobe_path)}")

from pydub import utils as pydub_utils

orig_mediainfo_json = pydub_utils.mediainfo_json

def debug_mediainfo_json(filepath, read_ahead_limit=0):
    command = [AudioSegment.ffprobe, "-v", "quiet", "-print_format", "json", "-show_format", "-show_streams", filepath]
    print(f"[DEBUG] mediainfo command: {command}")
    return orig_mediainfo_json(filepath, read_ahead_limit=read_ahead_limit)

pydub_utils.mediainfo_json = debug_mediainfo_json


# ✅ Load secrets logic (local vs Azure)
if os.path.exists(".env.local"):
    print("[🔑] Loaded secrets from .env.local (local mode)")
    load_dotenv(".env.local")
else:
    print("[☁️] Using Azure App Service environment variables")

# ✅ Common environment vars
IRSLOGICS_API_KEY = os.getenv("IRSLOGICS_API_KEY")
IRSLOGICS_UPLOAD_URL = "https://choice.irslogics.com/publicapi/documents/casedocument"
CLIENT_ID = os.getenv("RINGCENTRAL_CLIENT_ID")
CLIENT_SECRET = os.getenv("RINGCENTRAL_CLIENT_SECRET")
BASE_URL = os.getenv("RINGCENTRAL_BASE_URL", "https://platform.ringcentral.com")
TOKEN_URL = f"{BASE_URL}/restapi/oauth/token"

# Input file directory
TEMP_DIR = "/tmp/temp_recordings"
os.makedirs(TEMP_DIR, exist_ok=True)

# File size thresholds
MAX_MB = 5.99
MAX_BYTES = MAX_MB * 1024 * 1024  # ~6,285,824 bytes



def split_mp3_if_needed(filepath, force_split=False):


    try:
        file_size = os.path.getsize(filepath)
    except FileNotFoundError:
        print(f"[❌] File not found for splitting: {filepath}")
        return []

    if file_size <= MAX_BYTES and not force_split:
        return [filepath]  # No split needed unless forced

    print(f"[⚠️] File exceeds {MAX_MB} MB or forced split. Splitting...")

    try:
        print(f"\n[DEBUG] Preparing to split file: {filepath}")
        print(f"[DEBUG] File exists? {os.path.exists(filepath)}")
        if os.path.exists(filepath):
            print(f"[DEBUG] File size: {os.path.getsize(filepath)} bytes")
            
        print(f"[DEBUG] ffmpeg_path: {AudioSegment.converter}")
        print(f"[DEBUG] ffprobe_path: {AudioSegment.ffprobe}")
        audio = AudioSegment.from_mp3(filepath)
    except Exception as e:
        print(f"[❌] Error during AudioSegment.from_mp3: {e}")
        raise

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

    if os.path.exists(filepath):
        os.remove(filepath)

    return new_files




def get_access_token_from_refresh_token():
    print("[🔄] Exchanging refresh token for access token...")
    refresh_token = load_refresh_token()  # ✅ read from /home/refresh_token.txt or fallback to env

    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token
    }

    auth = (CLIENT_ID, CLIENT_SECRET)
    response = requests.post(TOKEN_URL, data=data, auth=auth)

    if response.status_code != 200:
        print("❌ Error response from RingCentral:")
        print("Status Code:", response.status_code)
        print("Response:", response.text)
        response.raise_for_status()

    token_data = response.json()
    access_token = token_data["access_token"]

    # Save new refresh token if provided
    if "refresh_token" in token_data:
        save_refresh_token(token_data["refresh_token"])  # ✅ write to /home/refresh_token.txt

    print("[✅] Got access token.")
    return access_token




# def get_access_token_from_refresh_token():
#     from dotenv import load_dotenv
#     # Only load .env.local if it exists (for local development)
#     if os.path.exists(".env.local"):
#         load_dotenv(".env.local", override=True)

#     client_id = os.getenv("RINGCENTRAL_CLIENT_ID")
#     client_secret = os.getenv("RINGCENTRAL_CLIENT_SECRET")
#     refresh_token = os.getenv("RINGCENTRAL_REFRESH_TOKEN")
#     base_url = os.getenv("RINGCENTRAL_BASE_URL", "https://platform.ringcentral.com")
#     token_url = f"{base_url}/restapi/oauth/token"

#     print("[🔄] Exchanging refresh token for access token...")
#     print(f"[🔐] Using refresh token: {refresh_token[:6]}... (truncated)")
#     print(f"[🌐] Token URL: {token_url}")

#     data = {
#         "grant_type": "refresh_token",
#         "refresh_token": refresh_token
#     }

#     auth = (client_id, client_secret)
#     response = requests.post(token_url, data=data, auth=auth)

#     if response.status_code != 200:
#         print("❌ Error response from RingCentral:")
#         print("Status Code:", response.status_code)
#         print("Response:", response.text)
#         print(f"[DEBUG] client_id: {client_id[:6]}..., client_secret: {client_secret[:6]}...")
#         response.raise_for_status()

#     token_data = response.json()
#     access_token = token_data["access_token"]

#     # Update refresh token if returned
#     if "refresh_token" in token_data:
#         update_refresh_token_env(token_data["refresh_token"])
#         print("[✅] New refresh token saved to .env.local.")

#     print("[✅] Got access token.")
#     return access_token



# def update_refresh_token_env(new_token, env_path=".env.local"):
#     print("[💾] Updating .env.local with new refresh token...")
#     lines = []
#     updated = False

#     # Read existing lines
#     with open(env_path, "r") as f:
#         for line in f:
#             if line.startswith("RINGCENTRAL_REFRESH_TOKEN="):
#                 lines.append(f"RINGCENTRAL_REFRESH_TOKEN={new_token}\n")
#                 updated = True
#             else:
#                 lines.append(line)

#     # If token wasn't found, append it
#     if not updated:
#         lines.append(f"RINGCENTRAL_REFRESH_TOKEN={new_token}\n")

#     # Write back the updated content
#     with open(env_path, "w") as f:
#         f.writelines(lines)

#     print("[✅] .env.local updated.")


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

def upload_call_recordings_to_irslogics(merged_calls_file_path=None):
    if not merged_calls_file_path:
        merged_calls_file_path = get_latest_json_file("irs_matched_calls_cache")
    print(f"[📁] Using merged calls file: {merged_calls_file_path}")
    access_token = get_access_token_from_refresh_token()

    # Load matched calls
    with open(merged_calls_file_path, "r") as f:
        call_logs = json.load(f)
        
    # Only process calls that haven't been marked as uploaded
    calls_to_upload = [c for c in call_logs if not c.get("uploaded")]

    if not calls_to_upload:
        print("✅ All calls in this file have already been uploaded. Nothing to do.")
        return

    success_count = 0

    # Load previously uploaded call_ids from latest merged_calls_with_case_id
    previous_log = get_latest_json_file("/tmp/irs_matched_calls_cache")
    with open(previous_log, "r") as f:
        previously_uploaded = {entry["call_id"] for entry in json.load(f)}


    for i, call in enumerate(call_logs, start=1):
        call_id = call["call_id"]
        case_id = call["CaseID"]
        recording_uri = call["recording_uri"]
        start_time = call.get("startTime")
        filename = format_filename(start_time)

        print(f"\n[{i}/{len(call_logs)}] Processing call {call_id} for CaseID {case_id}")

        # if call_id in previously_uploaded:
        #     print(f"[⏩] Skipping previously uploaded call: {call_id}")
        #     continue

        # Download recording
        if not download_recording(recording_uri, access_token, filename):
            continue

        # Split if needed
        file_list = split_mp3_if_needed(filename)

            # Upload each file (original or split parts)
        for f in file_list:
            basename = os.path.basename(f)

            # Attempt upload
            success = upload_to_irslogics(case_id, f)

            # Fallback if upload failed AND it's not already a split part
            if not success and "_part" not in f:
                print(f"[🔁] Upload failed (non-200). Attempting fallback split for: {f}")

                # 🔄 Split the file first
                fallback_parts = split_mp3_if_needed(f, force_split=True)

                if not fallback_parts:
                    print(f"[⚠️] No fallback parts created for {f}. Skipping...")
                    continue

                print(f"[🔀] Fallback split created {len(fallback_parts)} parts:")

                for idx, part in enumerate(fallback_parts, 1):
                    print(f"  [🎧 Part {idx}] {part}")

                # ✅ Don't try to upload `f` again — it's deleted. Upload each part instead.
                for part in fallback_parts:
                    if upload_to_irslogics(case_id, part):
                        success_count += 1
                    else:
                        print(f"[❌] Failed to upload fallback part: {part}")

                    # Clean up each part
                    if os.path.exists(part):
                        os.remove(part)

                continue  # ✅ Skip the rest of the loop since we already handled this case



            elif success:
                success_count += 1
                if os.path.exists(f):
                    os.remove(f)


        time.sleep(2.5)  # Optional: throttle requests

    print(f"\n[✅] Upload complete. Successful uploads: {success_count}/{len(call_logs)}")


if __name__ == "__main__":
    upload_call_recordings_to_irslogics()
