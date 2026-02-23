import requests
from config import UNITIME_BASE_URL, USERNAME, PASSWORD

def get_existing_courses():
    url = f"{UNITIME_BASE_URL}/api/courses"

    response = requests.get(
        url,
        auth=(USERNAME, PASSWORD)
    )

    if response.status_code != 200:
        raise Exception("Failed to fetch courses from UniTime")

    data = response.json()

    existing = set()

    for course in data:
        subject_area = course["subjectArea"]
        course_number = course["courseNumber"]
        existing.add((subject_area, course_number))

    return existing