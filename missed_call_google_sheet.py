import json
import os
import time
from html import escape
from datetime import datetime, timedelta

import pytz
import requests
from dotenv import load_dotenv
from google.oauth2 import service_account
from googleapiclient.discovery import build

from irs_logics_fetch_case_information import fetch_and_cache_irs_logics_cases
from irs_logics_fetch_cases_by_status_ids import fetch_and_cache_case_ids
from ring_central_fetch_calls import BASE_URL, format_phone_number, get_access_token_from_refresh_token
from storage_utils import load_latest_json, save_json


CALL_LOG_URL = f"{BASE_URL}/restapi/v1.0/account/~/call-log"
PACIFIC = pytz.timezone("US/Pacific")
RINGCENTRAL_HEADERS = ["From", "To", "Name", "Date", "Time (Pacific)", "Action", "Result"]
MANUAL_HEADERS = ["Followed Up By", "IRS Logics Case ID", "Notes"]
SHEET_HEADERS = RINGCENTRAL_HEADERS + MANUAL_HEADERS
SHEET_RANGE = "A:J"
MAX_RINGCENTRAL_RETRIES = 5
EMAIL_TO = "isabella@choicetaxrelief.com"
EMAIL_CC = ["danny.guerra@choicetaxrelief.com", "hailey.ritter@choicetaxrelief.com"]


def _load_env():
    if os.path.exists(".env.local"):
        load_dotenv(".env.local", override=True)


def _parse_days_back() -> int:
    raw = os.getenv("MISSED_CALLS_DAYS_BACK", "7")
    try:
        return max(1, int(raw))
    except ValueError:
        return 7


def _normalize_phone(phone):
    if not phone:
        return None
    return format_phone_number(phone)


def _phone_key(phone):
    if not phone:
        return ""
    return "".join(ch for ch in str(phone) if ch.isdigit())[-10:]


def _format_ringcentral_name(call):
    from_info = call.get("from", {}) or {}
    caller_name = from_info.get("name") or from_info.get("extensionName")
    return caller_name or ""


def _format_pacific_date_time(start_time):
    if not start_time:
        return "", ""
    try:
        utc_dt = datetime.strptime(start_time, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=pytz.utc)
    except ValueError:
        try:
            utc_dt = datetime.strptime(start_time, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=pytz.utc)
        except ValueError:
            return start_time, ""

    local_dt = utc_dt.astimezone(PACIFIC)
    return local_dt.strftime("%Y-%m-%d"), local_dt.strftime("%I:%M %p")


def _load_service_account_info():
    raw_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
    json_path = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE")

    if raw_json:
        return json.loads(raw_json)
    if json_path:
        with open(json_path, "r", encoding="utf-8") as f:
            return json.load(f)

    raise RuntimeError(
        "Missing Google credentials. Set GOOGLE_SERVICE_ACCOUNT_JSON or GOOGLE_SERVICE_ACCOUNT_FILE."
    )


def _build_sheets_service():
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    credentials = service_account.Credentials.from_service_account_info(
        _load_service_account_info(),
        scopes=scopes,
    )
    return build("sheets", "v4", credentials=credentials, cache_discovery=False)


def fetch_missed_ringcentral_calls(days_back=None):
    _load_env()
    days = days_back or _parse_days_back()
    access_token = get_access_token_from_refresh_token()
    from_date = (datetime.utcnow() - timedelta(days=days)).isoformat() + "Z"

    params = {
        "dateFrom": from_date,
        "perPage": 1000,
        "direction": "Inbound",
    }
    headers = {"Authorization": f"Bearer {access_token}"}

    records = []
    page = 1
    while True:
        params["page"] = page
        for attempt in range(1, MAX_RINGCENTRAL_RETRIES + 1):
            response = requests.get(CALL_LOG_URL, headers=headers, params=params, timeout=30)
            if response.status_code != 429:
                response.raise_for_status()
                break

            retry_after = response.headers.get("Retry-After")
            try:
                wait_seconds = int(retry_after) if retry_after else 30 * attempt
            except ValueError:
                wait_seconds = 30 * attempt

            print(
                f"[Missed Calls] RingCentral rate limit hit on page {page}. "
                f"Retrying in {wait_seconds}s ({attempt}/{MAX_RINGCENTRAL_RETRIES})."
            )
            time.sleep(wait_seconds)
        else:
            response.raise_for_status()

        payload = response.json()
        records.extend(payload.get("records", []))

        navigation = payload.get("navigation", {}) or {}
        if not navigation.get("nextPage"):
            break
        page += 1

    missed = [call for call in records if call.get("result") == "Missed"]
    print(f"[Missed Calls] Fetched {len(records)} inbound calls; {len(missed)} were missed.")
    return missed


def load_current_logics_phone_keys(refresh_cases=False):
    if refresh_cases:
        fetch_and_cache_case_ids()
        fetch_and_cache_irs_logics_cases()

    try:
        cases = load_latest_json("irs_logics_case_info_cache", "caseinfo")
    except FileNotFoundError:
        fetch_and_cache_case_ids()
        fetch_and_cache_irs_logics_cases()
        cases = load_latest_json("irs_logics_case_info_cache", "caseinfo")

    phone_keys = set()
    for case in cases:
        for field in ("CellPhone", "HomePhone", "WorkPhone"):
            key = _phone_key(case.get(field))
            if key:
                phone_keys.add(key)

    print(f"[Missed Calls] Loaded {len(phone_keys)} IRS Logics phone numbers.")
    return phone_keys


def build_unknown_missed_call_rows(calls, logics_phone_keys):
    rows = []
    seen_call_keys = set()

    for call in calls:
        from_number = _normalize_phone((call.get("from") or {}).get("phoneNumber"))
        to_number = _normalize_phone((call.get("to") or {}).get("phoneNumber"))
        from_key = _phone_key(from_number)

        if not from_key or from_key in logics_phone_keys:
            continue

        date_value, time_value = _format_pacific_date_time(call.get("startTime"))
        call_key = (from_key, date_value, time_value)
        if call_key in seen_call_keys:
            continue
        seen_call_keys.add(call_key)

        rows.append(
            [
                from_number,
                to_number,
                _format_ringcentral_name(call),
                date_value,
                time_value,
                call.get("action", ""),
                call.get("result", ""),
            ]
        )

    print(f"[Missed Calls] Built {len(rows)} new candidate rows.")
    return rows


def _get_existing_sheet_values(service, spreadsheet_id, sheet_range):
    result = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=spreadsheet_id, range=sheet_range)
        .execute()
    )
    return result.get("values", [])


def _ensure_sheet_exists(service, spreadsheet_id, sheet_name):
    metadata = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    sheets = metadata.get("sheets", [])
    existing_names = {
        sheet.get("properties", {}).get("title")
        for sheet in sheets
    }

    if sheet_name in existing_names:
        return

    service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body={
            "requests": [
                {
                    "addSheet": {
                        "properties": {
                            "title": sheet_name
                        }
                    }
                }
            ]
        },
    ).execute()


def _get_sheet_id(service, spreadsheet_id, sheet_name):
    metadata = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    for sheet in metadata.get("sheets", []):
        properties = sheet.get("properties", {})
        if properties.get("title") == sheet_name:
            return properties.get("sheetId")
    raise RuntimeError(f"Sheet tab not found after creation: {sheet_name}")


def _ensure_headers(service, spreadsheet_id, sheet_name):
    _ensure_sheet_exists(service, spreadsheet_id, sheet_name)
    values = _get_existing_sheet_values(service, spreadsheet_id, f"{sheet_name}!A1:J1")
    if values and values[0] == SHEET_HEADERS:
        return

    service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range=f"{sheet_name}!A1:J1",
        valueInputOption="RAW",
        body={"values": [SHEET_HEADERS]},
    ).execute()


def _sort_sheet_newest_first(service, spreadsheet_id, sheet_name):
    sheet_id = _get_sheet_id(service, spreadsheet_id, sheet_name)
    service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body={
            "requests": [
                {
                    "sortRange": {
                        "range": {
                            "sheetId": sheet_id,
                            "startRowIndex": 1,
                            "startColumnIndex": 0,
                            "endColumnIndex": len(SHEET_HEADERS),
                        },
                        "sortSpecs": [
                            {
                                "dimensionIndex": 3,
                                "sortOrder": "DESCENDING",
                            },
                            {
                                "dimensionIndex": 4,
                                "sortOrder": "DESCENDING",
                            },
                        ],
                    }
                }
            ]
        },
    ).execute()


def _rewrite_sheet_without_duplicates(service, spreadsheet_id, sheet_name):
    values = _get_existing_sheet_values(service, spreadsheet_id, f"{sheet_name}!{SHEET_RANGE}")
    if not values:
        return 0

    unique_rows = []
    seen_keys = set()
    duplicates_removed = 0

    for row in values[1:]:
        padded = row + [""] * (len(SHEET_HEADERS) - len(row))
        normalized_row = padded[:len(SHEET_HEADERS)]
        key = (_phone_key(normalized_row[0]), normalized_row[3], normalized_row[4])

        if key[0] and key[1] and key[2]:
            if key in seen_keys:
                duplicates_removed += 1
                continue
            seen_keys.add(key)

        unique_rows.append(normalized_row)

    if duplicates_removed == 0:
        return 0

    service.spreadsheets().values().clear(
        spreadsheetId=spreadsheet_id,
        range=f"{sheet_name}!{SHEET_RANGE}",
        body={},
    ).execute()
    service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range=f"{sheet_name}!A1:J{len(unique_rows) + 1}",
        valueInputOption="USER_ENTERED",
        body={"values": [SHEET_HEADERS] + unique_rows},
    ).execute()
    print(f"[Missed Calls] Removed {duplicates_removed} duplicate Google Sheet rows.")
    return duplicates_removed


def _existing_row_keys(values):
    keys = set()
    for row in values[1:]:
        padded = row + [""] * (len(SHEET_HEADERS) - len(row))
        from_key = _phone_key(padded[0])
        date_value = padded[3]
        time_value = padded[4]
        if from_key and date_value and time_value:
            keys.add((from_key, date_value, time_value))
    return keys


def append_rows_to_google_sheet(rows):
    _load_env()
    spreadsheet_id = os.getenv("MISSED_CALLS_SPREADSHEET_ID")
    sheet_name = os.getenv("MISSED_CALLS_SHEET_NAME", "Missed Calls")

    if not spreadsheet_id:
        raise RuntimeError("Missing MISSED_CALLS_SPREADSHEET_ID.")

    service = _build_sheets_service()
    _ensure_headers(service, spreadsheet_id, sheet_name)

    existing_values = _get_existing_sheet_values(service, spreadsheet_id, f"{sheet_name}!{SHEET_RANGE}")
    existing_keys = _existing_row_keys(existing_values)

    new_rows = []
    for row in rows:
        key = (_phone_key(row[0]), row[3], row[4])
        if key not in existing_keys:
            new_rows.append(row)
            existing_keys.add(key)

    if not new_rows:
        print("[Missed Calls] No new rows to append.")
        _rewrite_sheet_without_duplicates(service, spreadsheet_id, sheet_name)
        _sort_sheet_newest_first(service, spreadsheet_id, sheet_name)
        return []

    service.spreadsheets().values().append(
        spreadsheetId=spreadsheet_id,
        range=f"{sheet_name}!{SHEET_RANGE}",
        valueInputOption="USER_ENTERED",
        insertDataOption="INSERT_ROWS",
        body={"values": new_rows},
    ).execute()
    _rewrite_sheet_without_duplicates(service, spreadsheet_id, sheet_name)
    _sort_sheet_newest_first(service, spreadsheet_id, sheet_name)
    print(f"[Missed Calls] Appended {len(new_rows)} rows to Google Sheets.")
    return new_rows


def _format_hour(dt):
    return dt.strftime("%I %p").lstrip("0")


def _email_timeframe(rows):
    call_times = []
    for row in rows:
        try:
            call_times.append(datetime.strptime(f"{row[3]} {row[4]}", "%Y-%m-%d %I:%M %p"))
        except (ValueError, IndexError):
            continue

    if not call_times:
        return "the latest hourly period"

    start = min(call_times).replace(minute=0, second=0, microsecond=0)
    end = max(call_times).replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    if start.date() == end.date():
        return f"{_format_hour(start)}-{_format_hour(end)} PT on {start.strftime('%B %d, %Y').replace(' 0', ' ')}"

    return (
        f"{start.strftime('%B %d, %Y').replace(' 0', ' ')} at {_format_hour(start)} PT through "
        f"{end.strftime('%B %d, %Y').replace(' 0', ' ')} at {_format_hour(end)} PT"
    )


def _build_email_html(rows, sheet_url, timeframe):
    table_rows = []
    for row in rows:
        cells = "".join(
            f'<td style="padding:8px;border:1px solid #d1d5db">{escape(str(value or ""))}</td>'
            for value in row
        )
        table_rows.append(f"<tr>{cells}</tr>")

    headers = "".join(
        f'<th style="padding:8px;border:1px solid #d1d5db;text-align:left">{escape(header)}</th>'
        for header in RINGCENTRAL_HEADERS
    )
    return (
        "<p>Hello Isabella,</p>"
        f"<p>{len(rows)} new missed call{'s were' if len(rows) != 1 else ' was'} received between {escape(timeframe)}. "
        "Please review the details below and return the calls when you are able.</p>"
        '<table style="border-collapse:collapse;font-family:Arial,sans-serif;font-size:13px">'
        f"<thead><tr>{headers}</tr></thead><tbody>{''.join(table_rows)}</tbody></table>"
        f'<p><a href="{escape(sheet_url, quote=True)}">Open the missed-calls Google Sheet</a></p>'
        "<p>Thank you.</p>"
    )


def send_new_missed_calls_notification(rows):
    _load_env()
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_username = os.getenv("SMTP_USERNAME")
    smtp_password = os.getenv("SMTP_PASSWORD")
    from_email = os.getenv("NOTIFY_FROM_EMAIL", smtp_username)
    to_email = EMAIL_TO
    cc_emails = EMAIL_CC

    if not all((smtp_host, smtp_username, smtp_password, from_email, to_email)):
        print("[Missed Calls] SMTP settings are incomplete; notification skipped.")
        return "skipped"

    import smtplib
    from email.mime.text import MIMEText

    spreadsheet_id = os.getenv("MISSED_CALLS_SPREADSHEET_ID")
    sheet_url = os.getenv(
        "MISSED_CALLS_SHEET_URL",
        f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit?usp=sharing",
    )
    timeframe = _email_timeframe(rows)
    message = MIMEText(_build_email_html(rows, sheet_url, timeframe), "html")
    message["Subject"] = (
        f"{len(rows)} New Missed Call{'s' if len(rows) != 1 else ''} from {timeframe}"
    )
    message["From"] = from_email
    message["To"] = to_email
    if cc_emails:
        message["Cc"] = ", ".join(cc_emails)

    with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as server:
        server.starttls()
        server.login(smtp_username, smtp_password)
        server.send_message(message, from_addr=from_email, to_addrs=[to_email] + cc_emails)

    print(f"[Missed Calls] Email notification sent for {len(rows)} new calls.")
    return "sent"


def populate_missed_calls_google_sheet(days_back=None, refresh_cases=False):
    missed_calls = fetch_missed_ringcentral_calls(days_back=days_back)
    logics_phone_keys = load_current_logics_phone_keys(refresh_cases=refresh_cases)
    rows = build_unknown_missed_call_rows(missed_calls, logics_phone_keys)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    save_json(
        rows,
        "missed_calls_cache",
        f"unknown_missed_calls_{timestamp}.json",
        "unknownmissedcalls",
    )

    appended_rows = append_rows_to_google_sheet(rows)
    email_status = "not_needed"
    if appended_rows:
        try:
            email_status = send_new_missed_calls_notification(appended_rows)
        except Exception as exc:
            email_status = f"failed: {exc}"
            print(f"[Missed Calls] Email notification failed: {exc}")

    return {
        "candidate_rows": len(rows),
        "appended_rows": len(appended_rows),
        "email_status": email_status,
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Populate Google Sheets with unknown missed RingCentral calls.")
    parser.add_argument("--days-back", type=int, default=None, help="Override MISSED_CALLS_DAYS_BACK.")
    parser.add_argument(
        "--refresh-cases",
        action="store_true",
        help="Refresh IRS Logics case caches before filtering missed calls.",
    )
    args = parser.parse_args()

    print(populate_missed_calls_google_sheet(days_back=args.days_back, refresh_cases=args.refresh_cases))
