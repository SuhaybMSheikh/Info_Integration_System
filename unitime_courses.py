import requests
from config import UNITIME_BASE_URL, USERNAME, PASSWORD

def get_existing_courses():
    url = f"{UNITIME_BASE_URL}/api/courses"

    try:
        response = requests.get(
            url,
            auth=(USERNAME, PASSWORD),
            timeout=30
        )

        print("Status Code:", response.status_code)
        print("Response Text:", response.text)

        if response.status_code != 200:
            raise Exception(
                f"Failed to fetch courses from UniTime\n"
                f"Status: {response.status_code}\n"
                f"Response: {response.text}"
            )

        data = response.json()

        courses = {}

        for offering in data:

            subject = offering["subject"]
            number = offering["courseNumber"]

            configs = {}

            for config in offering.get("configurations", []):
                config_name = config["name"]

                configs[config_name] = {
                    "classes": {
                        c["externalId"]: c
                        for c in config.get("classes", [])
                    }
                }

            courses[(subject, number)] = {
                "configurations": configs
            }

        return courses

    except requests.exceptions.RequestException as e:
        raise e