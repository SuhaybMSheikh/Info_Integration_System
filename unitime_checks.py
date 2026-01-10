import requests
from config import UNITIME_BASE_URL, USERNAME, PASSWORD

def check_curriculum_exists(code: str) -> bool:
    url = f"{UNITIME_BASE_URL}/api/curricula"
    r = requests.get(url, auth=(USERNAME, PASSWORD))
    return code in r.text

def validate_faculties_exist(client, records):
    faculties_in_data = {r["faculty"] for r in records}

    existing = client.get_departments()  # returns { "APP": id, "ATA": id }

    missing = faculties_in_data - existing.keys()
    if missing:
        raise RuntimeError(
            f"Missing departments in UniTime: {', '.join(missing)}"
        )

    return existing