import requests
from config import UNITIME_BASE_URL, USERNAME, PASSWORD

def check_curriculum_exists(code: str) -> bool:
    url = f"{UNITIME_BASE_URL}/api/curricula"
    r = requests.get(url, auth=(USERNAME, PASSWORD))
    return code in r.text