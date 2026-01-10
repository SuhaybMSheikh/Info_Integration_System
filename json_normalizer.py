from collections import defaultdict
from datetime import datetime

def normalize_rows(rows: list[dict]) -> dict:
    modules = defaultdict(lambda: {
        "instructionalOfferings": []
    })
    curricula = {}
    instructors = {}

    for row in rows:
        course_code = row["Subjects"].split("-")[0]
        subject_area = row["Subjects"].split("-")[3]

        intake_codes = [
            i.split("(")[0].strip()
            for i in row["Intakes"].split(",")
        ]

        instructors[row["Lecturer Code"]] = row["Lecturer Name"]

        modules[(subject_area, course_code)]["subjectArea"] = subject_area
        modules[(subject_area, course_code)]["courseCode"] = course_code
        modules[(subject_area, course_code)]["title"] = course_code

        modules[(subject_area, course_code)]["instructionalOfferings"].append({
            "intakes": intake_codes,
            "class": {
                "classCode": row["Class Code"],
                "instructor": row["Lecturer Code"],
                "durationMinutes": row["Class Duration"],
                "weeks": int(row["Duration (weeks)"]),
                "weekBegins": row["Week Begins"],
                "expectedStudents": int(row["Total Students"])
            }
        })

        for intake in intake_codes:
            curricula.setdefault(intake, {"code": intake})

    return {
        "modules": list(modules.values()),
        "instructors": instructors,
        "curricula": list(curricula.values())
    }