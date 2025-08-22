# ringcentral-to-irslogics
2025-08-22T02:33:04.5776159Z ⬆️ Step 5: Uploading call recordings to IRS Logics...
2025-08-22T02:33:04.5776192Z [📁] Using merged calls file: /tmp/irs_matched_calls_cache/merged_calls_with_case_id_2025-08-22_02-32-58.json
2025-08-22T02:33:04.5776208Z [🔄] Exchanging refresh token for access token...
2025-08-22T02:33:04.5776292Z [🔑] Loaded refresh token from /home/refresh_token.txt
2025-08-22T02:33:04.5776309Z [💾] Refresh token updated in /home/refresh_token.txt
2025-08-22T02:33:04.5776325Z [✅] Got access token.
2025-08-22T02:33:04.5776338Z
2025-08-22T02:33:04.5776355Z [1/387] Processing call AIMXHgQ3lTCQnc1A for CaseID 30516
2025-08-22T02:33:04.5776373Z [⬇️] Downloaded to /tmp/temp_recordings/call_2025-08-21 04-28-34 PM PDT.mp3
2025-08-22T02:33:04.5776390Z [⚠️] File exceeds 5.99 MB or forced split. Splitting...
2025-08-22T02:33:04.5776410Z 2025-08-22 02:33:04,346 [ERROR] ❌ Automation failed in background: [Errno 2] No such file or directory: 'ffprobe'
2025-08-22T02:33:04.5776426Z Traceback (most recent call last):
2025-08-22T02:33:04.5776457Z   File "/tmp/8dde11567e32216/server.py", line 29, in run_job
2025-08-22T02:33:04.5776473Z     automate_ringcentral_to_irslogics()
2025-08-22T02:33:04.5776492Z   File "/tmp/8dde11567e32216/automate_ringcentral_to_irslogics.py", line 35, in automate_ringcentral_to_irslogics
2025-08-22T02:33:04.5776508Z     upload_call_recordings_to_irslogics()
2025-08-22T02:33:04.5776526Z   File "/tmp/8dde11567e32216/irs_logics_upload_call_recordings.py", line 304, in upload_call_recordings_to_irslogics
2025-08-22T02:33:04.5776542Z     file_list = split_mp3_if_needed(filename)
2025-08-22T02:33:04.5776558Z                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
2025-08-22T02:33:04.5776575Z   File "/tmp/8dde11567e32216/irs_logics_upload_call_recordings.py", line 80, in split_mp3_if_needed
2025-08-22T02:33:04.5776591Z     audio = AudioSegment.from_mp3(filepath)
2025-08-22T02:33:04.5776607Z             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
2025-08-22T02:33:04.5776641Z   File "/tmp/8dde11567e32216/antenv/lib/python3.12/site-packages/pydub/audio_segment.py", line 796, in from_mp3
2025-08-22T02:33:04.5776657Z     return cls.from_file(file, 'mp3', parameters=parameters)
2025-08-22T02:33:04.5776673Z            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
2025-08-22T02:33:04.5776691Z   File "/tmp/8dde11567e32216/antenv/lib/python3.12/site-packages/pydub/audio_segment.py", line 728, in from_file
2025-08-22T02:33:04.5776708Z     info = mediainfo_json(orig_file, read_ahead_limit=read_ahead_limit)
2025-08-22T02:33:04.5776724Z            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
2025-08-22T02:33:04.5776743Z   File "/tmp/8dde11567e32216/antenv/lib/python3.12/site-packages/pydub/utils.py", line 274, in mediainfo_json
2025-08-22T02:33:04.5776760Z     res = Popen(command, stdin=stdin_parameter, stdout=PIPE, stderr=PIPE)
2025-08-22T02:33:04.5777004Z           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
2025-08-22T02:33:04.5777026Z   File "/opt/python/3.12.11/lib/python3.12/subprocess.py", line 1026, in __init__
2025-08-22T02:33:04.5777060Z     self._execute_child(args, executable, preexec_fn, close_fds,
2025-08-22T02:33:04.5777077Z   File "/opt/python/3.12.11/lib/python3.12/subprocess.py", line 1955, in _execute_child
2025-08-22T02:33:04.5777093Z     raise child_exception_type(errno_num, err_msg, err_filename)
2025-08-22T02:33:04.5777109Z FileNotFoundError: [Errno 2] No such file or directory: 'ffprobe'


to deploy:
az login --use-device-code  

func azure functionapp publish ringcentral-irs-logics-automated --python

to test manual automation endpoint deployed version

Invoke-WebRequest -Uri "https://flex-ring-central-irs-logics-automated-gwb5acekapfabphw.westus3-01.azurewebsites.net/api/run-automation?code=dlXZCdcZ3vr2CERIR8r9DClfcR7kuYNulBEB5FGr-8DrAzFuJ6mfDQ==" -Method GET


to test locally:

func start

curl http://localhost:7071/api/run-automation


log stated:
Your WeeklyAutomation function will now run automatically at:

Aug 25, 2025 – 02:00 UTC

Sep 1, 2025 – 02:00 UTC

Sep 8, 2025 – 02:00 UTC

Sep 15, 2025 – 02:00 UTC

Sep 22, 2025 – 02:00 UTC

📞🔗 IRS Logics + RingCentral Automation Workflow
This automation system integrates RingCentral call logs with IRS Logics case records. It processes call recordings, matches them to IRS cases via phone numbers, and uploads valid recordings to the IRS Logics system.

🚀 Overview
The core automation is executed via the automate_ringcentral_to_irslogics() function, which orchestrates the following 5 steps:

🔁 Workflow Breakdown
📞 Step 1: Fetch RingCentral Call Logs
Function: fetch_and_cache_ringcentral_calls()

Action: Retrieves call logs from RingCentral using a refresh token.

Filters: Includes only sales team numbers and calls with recordings.

Output:

✅ JSON cache: ring_central_call_logs_cache/calls_<timestamp>.json

🎙 First recording downloaded to local .mp3 for verification.

📄 Step 2: Fetch IRS Logics Case IDs by StatusID
Function: fetch_and_cache_case_ids()

Action: Pulls CaseIDs grouped by StatusID from IRS Logics API.

Optimized: Compares against previous logs to avoid redundant fetches.

Output:

📁 JSON cache: irs_logics_case_ids_cache/all_case_ids_<timestamp>.json

📂 Step 3: Fetch IRS Logics Case Info (Phone Numbers)
Function: fetch_and_cache_irs_logics_cases()

Action: Fetches full contact details (Name, CellPhone, etc.) for each CaseID.

Optimized: Optional deduping if same CaseID already exists in previous logs.

Output:

🧾 JSON cache: irs_logics_case_info_cache/all_cases_with_numbers_<timestamp>.json

🔗 Step 4: Match Calls to IRS Logics Cases
Function: match_calls_to_cases(call_log_path, case_log_path)

Action: Cross-matches client_number from RingCentral calls with any of:

CellPhone, HomePhone, or WorkPhone in case data.

Output:

✅ Matched: irs_matched_calls_cache/merged_calls_with_case_id_<timestamp>.json

⚠️ Unmatched: irs_unmatched_calls_cache/unmatched_calls_<timestamp>.json

⬆️ Step 5: Upload Recordings to IRS Logics
Function: upload_call_recordings_to_irslogics()

Action:

Downloads call recording via RingCentral API

Splits recording if it exceeds 5.99 MB

Uploads recording (or parts) to IRS Logics via document upload API

Smart Check: Skips uploading calls already present in the latest merged log.

Output:

🎧 MP3s stored temporarily in temp_recordings/ (auto-deleted after upload)

🪵 Console log shows detailed status for each call

🧠 Example Logs
Step	Folder	File Pattern	Purpose
Step 1	ring_central_call_logs_cache/	calls_<timestamp>.json	Fetched RingCentral call logs
Step 2	irs_logics_case_ids_cache/	all_case_ids_<timestamp>.json	Cached StatusID → CaseIDs
Step 3	irs_logics_case_info_cache/	all_cases_with_numbers_<timestamp>.json	Case contact info
Step 4	irs_matched_calls_cache/	merged_calls_with_case_id_<timestamp>.json	Matched calls with CaseIDs
Step 4	irs_unmatched_calls_cache/	unmatched_calls_<timestamp>.json	Calls with no matching case
Step 5	temp_recordings/	call_<timestamp>.mp3	Downloaded audio recordings
