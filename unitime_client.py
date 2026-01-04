import requests
from config import DATA_EXCHANGE_ENDPOINT, USERNAME, PASSWORD

def post_xml(xml_payload: str):
    headers = {"Content-Type": "application/xml"}

    response = requests.post(
        DATA_EXCHANGE_ENDPOINT,
        data=xml_payload.encode("utf-8"),
        headers=headers,
        auth=(USERNAME, PASSWORD),
        timeout=30
    )

    if response.status_code != 200:
        raise RuntimeError(f"HTTP {response.status_code}: {response.text}")

    if "<status>OK</status>" not in response.text:
        raise RuntimeError(f"UniTime rejected payload:\n{response.text}")

    return response.text