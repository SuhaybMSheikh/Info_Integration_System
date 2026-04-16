import requests
from config import UNITIME_BASE_URL, USERNAME, PASSWORD

def get_existing_classes():
    courses_url = f"{UNITIME_BASE_URL}/api/sectioning?operation=course-offerings&term=2026"

    response = requests.get(courses_url, auth=(USERNAME, PASSWORD))

    if response.status_code != 200:
        raise Exception("Failed to fetch course offerings")

    courses = response.json()

    existing = {}

    for course in courses:
        course_key = f"{course['subject']}_{course['courseNumber']}"

        classes_url = (
            f"{UNITIME_BASE_URL}/api/sectioning"
            f"?operation=classes"
            f"&term=2026"
            f"&course={course_key}"
        )

        cls_resp = requests.get(classes_url, auth=(USERNAME, PASSWORD))

        if cls_resp.status_code != 200:
            continue

        class_data = cls_resp.json()

        for cls in class_data:
            existing[cls["externalId"]] = {
                "limit": cls.get("limit"),
                "instructor": cls.get("instructorExternalId"),
                "weeks": cls.get("weeks"),
                "timePattern": cls.get("timePattern")
            }

    return existing