import requests
from config import UNITIME_BASE_URL, USERNAME, PASSWORD

def get_existing_classes():
    url = f"{UNITIME_BASE_URL}/api/classes"

    response = requests.get(
        url,
        auth=(USERNAME, PASSWORD)
    )

    if response.status_code != 200:
        raise Exception("Failed to fetch classes")

    data = response.json()

    existing = {}

    for cls in data:
        existing[cls["externalId"]] = {
            "limit": cls["limit"],
            "instructor": cls.get("instructorExternalId"),
            "weeks": cls.get("weeks"),
            "timePattern": cls.get("timePattern")
        }

    return existing