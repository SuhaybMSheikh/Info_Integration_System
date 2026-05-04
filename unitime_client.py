import requests
from datetime import datetime
from config import USERNAME, PASSWORD, DATA_EXCHANGE_ENDPOINT, UNITIME_BASE_URL, UNITIME_TOKEN
import logging
import json
import os
import time
import zipfile

logging.basicConfig(
    filename="integration.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# #region agent log
_DEBUG_LOG_PATH = "debug-583fc7.log"
_DEBUG_SESSION_ID = "583fc7"

def _debug_log(run_id: str, hypothesis_id: str, location: str, message: str, data: dict):
    try:
        payload = {
            "sessionId": _DEBUG_SESSION_ID,
            "runId": run_id,
            "hypothesisId": hypothesis_id,
            "location": location,
            "message": message,
            "data": data,
            "timestamp": int(time.time() * 1000),
        }
        with open(_DEBUG_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except Exception:
        pass
# #endregion

def post_xml(xml_data: str):
    headers = {
        "Content-Type": "application/xml"
    }

    print("\n--- Sending Data to UniTime ---")

    try:
        response = requests.post(
            DATA_EXCHANGE_ENDPOINT,
            params={
                "term": "2026",
                "type": "courseOfferings",
                "token": UNITIME_TOKEN
            },
            data=xml_data.encode("utf-8"),
            headers=headers,
            timeout=60
        )

        # 1 Print status code
        print(f"HTTP Status: {response.status_code}")
        logging.info(f"HTTP Status: {response.status_code}")

        # 2 Save full response to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_filename = f"unitime_response_{timestamp}.log"

        with open(log_filename, "w", encoding="utf-8") as f:
            f.write("STATUS: " + str(response.status_code) + "\n\n")
            f.write(response.text)

        print(f"Response saved to: {log_filename}")

        # 3 Print HTTP status errors; otherwise success
        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            error_msg = f"HTTP Status Error: {response.status_code} {response.reason}\n{response.text}"
            print(error_msg)
            logging.error(error_msg)
            raise e
        else:
            print("Import successful")
            logging.info("Import successful")

    except requests.exceptions.RequestException as e:
        print("\n Connection Error")
        raise e


def _post_xml_payload(xml_filename: str, xml_data: bytes):
    response = requests.post(
        DATA_EXCHANGE_ENDPOINT,
        params={"token": UNITIME_TOKEN},
        data=xml_data,
        headers={"Content-Type": "application/xml;charset=UTF-8"},
        timeout=120
    )

    return {
        "filename": xml_filename,
        "status": response.status_code,
        "body": response.text,
        "ok": response.status_code < 400,
    }


def _xml_payloads_from_file(snapshot_filename: str):
    if snapshot_filename.lower().endswith(".zip"):
        with zipfile.ZipFile(snapshot_filename) as unitime_zip:
            for name in unitime_zip.namelist():
                if name.lower().endswith(".xml"):
                    yield name, unitime_zip.read(name)
    else:
        with open(snapshot_filename, "rb") as f:
            yield os.path.basename(snapshot_filename), f.read()


def post_xml_file(snapshot_filename: str):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f"unitime_response_{timestamp}.log"

    print("\n--- Sending Data to UniTime ---")
    print(f"File: {snapshot_filename}")
    print(f"Endpoint: {DATA_EXCHANGE_ENDPOINT}")

    # #region agent log
    try:
        file_size = os.path.getsize(snapshot_filename)
    except Exception:
        file_size = None
    token_len = len(UNITIME_TOKEN) if isinstance(UNITIME_TOKEN, str) else None
    _debug_log(
        run_id="pre-fix",
        hypothesis_id="H1",
        location="unitime_client.py:post_xml_file",
        message="Preparing UniTime ZIP upload",
        data={
            "endpoint": DATA_EXCHANGE_ENDPOINT,
            "token_is_set": bool(UNITIME_TOKEN),
            "token_len": token_len,
            "file": snapshot_filename,
            "file_size_bytes": file_size,
        },
    )
    # #endregion

    try:
        payloads = list(_xml_payloads_from_file(snapshot_filename))
        if not payloads:
            raise Exception("No XML files found to import.")

        responses = []
        failed_response = None
        for xml_filename, xml_data in payloads:
            print(f"\nImporting {xml_filename}...")
            response_info = _post_xml_payload(xml_filename, xml_data)
            responses.append(response_info)

            print(f"HTTP Status: {response_info['status']}")
            print(response_info["body"])

            if not response_info["ok"]:
                logging.error(
                    f"UniTime import failed for {xml_filename}: "
                    f"{response_info['status']} {response_info['body']}"
                )
                failed_response = response_info
                break

        # #region agent log
        _debug_log(
            run_id="raw-xml-post",
            hypothesis_id="H2",
            location="unitime_client.py:post_xml_file",
            message="UniTime response received",
            data={
                "files_imported": [r["filename"] for r in responses],
                "statuses": [r["status"] for r in responses],
                "body_prefixes": [(r["body"] or "")[:200] for r in responses],
            },
        )
        # #endregion

        # Save full response to log file
        with open(log_filename, "w", encoding="utf-8") as f:
            for response_info in responses:
                f.write(f"=== {response_info['filename']} ===\n")
                f.write(f"HTTP STATUS: {response_info['status']}\n\n")
                f.write(response_info["body"])
                f.write("\n\n")

        print(f"Response saved to: {log_filename}")

        if failed_response:
            raise Exception(
                f"UniTime returned error response while importing {failed_response['filename']}."
            )

        print("Import successful")
        logging.info("Import successful")

    except requests.exceptions.RequestException as e:
        print("\n Connection Error")
        raise e

# def get_sessions():
#     url = f"{DATA_EXCHANGE_ENDPOINT}/sessions"

#     try:
#         response = requests.get(
#             url,
#             auth=(USERNAME, PASSWORD),
#             timeout=30
#         )

#         if response.status_code != 200:
#             raise Exception("Failed to fetch sessions")

#         return response.json()

#     except requests.exceptions.RequestException as e:
#         logging.error(f"Session fetch error: {str(e)}")
#         raise e
