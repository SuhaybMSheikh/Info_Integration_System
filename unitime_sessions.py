import requests
from config import UNITIME_BASE_URL, USERNAME, PASSWORD, UNITIME_TOKEN

def get_sessions():

    url = f"{UNITIME_BASE_URL}/api/sectioning?operation=academic-session"

    response = requests.get(
        url + f"&token={UNITIME_TOKEN}",
        timeout=30
    )

    if response.status_code != 200:
        raise Exception("Failed to fetch sessions from UniTime")

    return response.json()