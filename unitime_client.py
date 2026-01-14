import requests
from config import USERNAME, PASSWORD, DATA_EXCHANGE_ENDPOINT, UNITIME_BASE_URL

def post_xml(xml: str):
    r = requests.post(
        DATA_EXCHANGE_ENDPOINT,
        auth=(USERNAME, PASSWORD),
        headers={"Content-Type": "application/xml"},
        data=xml.encode("utf-8"),
        timeout=30
    )
    if r.status_code != 200 or "<status>OK</status>" not in r.text:
        raise RuntimeError(r.text)


def get_sessions():
    return requests.get(
        f"{UNITIME_BASE_URL}/api/sessions",
        auth=(USERNAME, PASSWORD)
    ).json()