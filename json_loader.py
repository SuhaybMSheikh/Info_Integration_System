import os
import requests
from config import API_BASE_URL, API_KEY, API_START_DATE, API_END_DATE


def fetch_api_payload():
    headers = {
        "X_API_KEY": API_KEY
    }

    params = {
        "start_date": API_START_DATE,
        "end_date": API_END_DATE
    }

    response = requests.get(
        API_BASE_URL,
        headers=headers,
        params=params,
        timeout=60
    )

    print("API Status Code:", response.status_code)
    print("Fetching schedules from API...")
    print("Date Range:", API_START_DATE, "to", API_END_DATE)

    if response.status_code != 200:
        raise Exception(
            f"Failed to fetch API data\n"
            f"Status: {response.status_code}\n"
            f"Response: {response.text}"
        )

    return response.json()


def flatten_api_payload(payload):
    records = []

    for block in payload:

        academic_session = block["academic_session"]
        week_begins = block["week_begins"]

        for subj in block["subjects"]:
            area = subj["subject"]["area"]
            full_code = subj["subject"]["code"]

            for cls in subj["classes"]:
                records.append({
                    "academic_session": academic_session,
                    "week_begins": week_begins,
                    "faculty": area,
                    "subject_raw": full_code,
                    "class_code": cls["code"],
                    "type_and_number": cls.get("type_and_number"),
                    "module_code": cls.get("module_code"),
                    "class_duration_raw": cls["duration"],
                    "duration_weeks": cls["weeks"],
                    "total_students": cls["number_of_students"],
                    "lecturer_code": cls["lecturer"]["code"] or "TBA",
                    "lecturer_name": cls["lecturer"]["username"] or "TBA",
                    "intakes": cls.get("intakes", [])
                })

    return records