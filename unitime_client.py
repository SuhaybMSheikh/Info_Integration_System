import requests
import subprocess
from datetime import datetime
from config import USERNAME, PASSWORD, DATA_EXCHANGE_ENDPOINT, UNITIME_BASE_URL, UNITIME_TOKEN
import logging
import json
import os
import time

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

    status_marker = "__CURL_HTTP_STATUS__:"
    curl_command = [
        "curl",
        "-k",
        "--silent",
        "--show-error",
        "-X", "POST",
        "-H", "Content-Type: application/zip",
        "--data-binary", f"@{snapshot_filename}",
        "-w", f"\\n{status_marker}%{{http_code}}\\n",
        f"{DATA_EXCHANGE_ENDPOINT}?token={UNITIME_TOKEN}"
    ]

    try:
        result = subprocess.run(
            curl_command,
            capture_output=True,
            text=True,
            timeout=120
        )

        print(f"Exit code: {result.returncode}")
        logging.info(f"curl exit code: {result.returncode}")

        # Extract HTTP status code appended by curl -w
        http_status = None
        body = result.stdout
        if status_marker in result.stdout:
            body, status_part = result.stdout.rsplit(status_marker, 1)
            body = body.rstrip("\r\n")
            status_str = status_part.strip().splitlines()[0] if status_part.strip() else ""
            if status_str.isdigit():
                http_status = int(status_str)

        # #region agent log
        _debug_log(
            run_id="pre-fix",
            hypothesis_id="H2",
            location="unitime_client.py:post_xml_file",
            message="UniTime response received",
            data={
                "curl_exit_code": result.returncode,
                "http_status": http_status,
                "stdout_len": len(result.stdout or ""),
                "stderr_len": len(result.stderr or ""),
                "body_prefix": (body or "")[:200],
            },
        )
        # #endregion

        # Save full response to log file
        with open(log_filename, "w", encoding="utf-8") as f:
            f.write(f"CURL EXIT CODE: {result.returncode}\n\n")
            if http_status is not None:
                f.write(f"HTTP STATUS: {http_status}\n\n")
            f.write("=== STDOUT ===\n")
            f.write(body)
            if result.stderr:
                f.write("\n=== STDERR ===\n")
                f.write(result.stderr)

        print(f"Response saved to: {log_filename}")
        print(body)

        # Fail loudly if curl itself failed
        if result.returncode != 0:
            logging.error(f"curl failed: {result.stderr}")
            raise Exception(f"curl command failed with exit code {result.returncode}:\n{result.stderr}")

        # Print HTTP status errors; otherwise success
        if http_status is not None and http_status >= 400:
            error_msg = f"HTTP Status Error: {http_status}\n{body}"
            print(error_msg)
            logging.error(error_msg)
            raise Exception("UniTime returned error response.")

        print("Import successful")
        logging.info("Import successful")

    except subprocess.TimeoutExpired:
        raise Exception("curl command timed out after 120 seconds")

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