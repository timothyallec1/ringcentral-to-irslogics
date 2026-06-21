
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





TO MANUALLY EDIT REFRESH_TOKEN.TXT on AZURE

1. go to bash console
    https://automated-ringcentral-irslogics-fra6hxard8aadwd9.scm.canadacentral-01.azurewebsites.net
    click BASH
    ls -l /home
    cat -A /home/refresh_token.txt
    printf '%s' 'PASTE_NEW_REFRESH_TOKEN_HERE' > /home/refresh_token.txt

    printf '%s' 'U0pDMDFQMjNQQVMwMHxBQUFHYmhpaXEwQkRidEFEdFZJdDBJR2tHc3V3TVdpX1g0ejlvbFdqa1IxNW1jYlpCM18yUk9oNHVsUE5HZDd1eklwdzVraXFUa2tpLVdCVkpEb2NfWW1CQVRXQnEwRmJaQlJDYW1NNTU4UGdpMlk2cE1ObjlFNVVBY3NtdVEtRVNmOXZJOThSLXp6S3J3V3FCSlhmUkdtSDJCTEY2V1NzVENJRWQ0d1lqbjVoUXZnWENTVjFXMmh5cm9Yd3dNZ2tHV1VGWVpXQVRZTXhiMGRNSmxaZ2kxNEFCVXF5ZUF8dERXcjdnfC1iYnVXTkQwR3lkRzlIV3FnQ21send8QVF8QUF8QUFBQUFQd3hKa0E' > /home/refresh_token.txt

    verify:
    cat -A /home/refresh_token.txt


Missed Calls Google Sheet

This repo also includes a separate workflow that collects inbound RingCentral calls with Result = Missed, removes phone numbers already found in IRS Logics case phone fields, and appends the remaining callers to a Google Sheet for callback.

Output columns:

- From
- To
- Name
- Date
- Time (Pacific)
- Action
- Result
- Followed Up By
- IRS Logics Case ID
- Notes

Azure Function routes:

- Scheduled: WeekdayMissedCallsSheet runs Monday-Friday at 14:00 UTC.
- Manual: /api/populate-missed-calls-sheet
- Optional backfill: /api/populate-missed-calls-sheet?days_back=30
- Combined daily manual route: /api/run-daily-ringcentral-automation

Required settings:

- MISSED_CALLS_SPREADSHEET_ID: Google Sheet ID from the spreadsheet URL.
- GOOGLE_SERVICE_ACCOUNT_JSON: full service account JSON as one app setting, or GOOGLE_SERVICE_ACCOUNT_FILE for local development.

Optional settings:

- MISSED_CALLS_SHEET_NAME: defaults to Missed Calls.
- MISSED_CALLS_DAYS_BACK: defaults to 7.
- MISSED_CALLS_SHEET_URL: optional shared Sheet URL used in notification emails.

Email notifications are sent only when rows are newly appended. They use the same SMTP
settings as choicetax-api: SMTP_HOST, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD, and
NOTIFY_FROM_EMAIL. Set NOTIFY_FROM_EMAIL to leads@choicetaxrelief.com.

Share the Google Sheet with the service account client_email before running the workflow.

