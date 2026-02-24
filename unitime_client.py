import requests
from datetime import datetime
from config import USERNAME, PASSWORD, DATA_EXCHANGE_ENDPOINT, UNITIME_BASE_URL
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
            data=xml_data.encode("utf-8"),
            headers=headers,
            auth=(USERNAME, PASSWORD),
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

        # 3 Fail loudly if error
        if response.status_code >= 400:
            logging.error(f"Import failed {response.text}")
            print(response.text)
            raise Exception("UniTime returned error response.")

        print("Import successful")
        logging.info("Import successful")

    except requests.exceptions.RequestException as e:
        print("\n Connection Error")
        raise e

def get_sessions():
    url = f"{DATA_EXCHANGE_ENDPOINT}/sessions"

    try:
        response = requests.get(
            url,
            auth=(USERNAME, PASSWORD),
            timeout=30
        )

        if response.status_code != 200:
            raise Exception("Failed to fetch sessions")

        return response.json()

    except requests.exceptions.RequestException as e:
        logging.error(f"Session fetch error: {str(e)}")
        raise e