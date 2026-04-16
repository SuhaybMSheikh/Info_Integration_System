# import requests
# from config import UNITIME_BASE_URL, USERNAME, PASSWORD

def get_existing_time_patterns():
    # url = f"{UNITIME_BASE_URL}/api/time-patterns"

    # response = requests.get(
    #     url,
    #     auth=(USERNAME, PASSWORD)
    # )

    # if response.status_code != 200:
    #     raise Exception("Failed to fetch time patterns from UniTime")

    # data = response.json()

    # # Extract names
    # return {tp["name"] for tp in data}
    return set()