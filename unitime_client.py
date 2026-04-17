import requests
import subprocess
from datetime import datetime
from config import USERNAME, PASSWORD, DATA_EXCHANGE_ENDPOINT, UNITIME_BASE_URL, UNITIME_TOKEN
import logging

logging.basicConfig(
    filename="integration.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

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

    status_marker = "__CURL_HTTP_STATUS__:"
    curl_command = [
        "curl",
        "-k",
        "--silent",
        "--show-error",
        "-X", "POST",
        "-H", "Content-Type: application/xml;charset=UTF-8",
        "-d", f"@{snapshot_filename}",
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