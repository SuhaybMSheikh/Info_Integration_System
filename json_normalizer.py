from collections import defaultdict
from time_utils import parse_duration_to_minutes, coerce_duration
from config import EXPECTED_ACADEMIC_SESSION


def normalize_records(records):

    normalized = []

    for r in records:

        # Academic session validation
        if r["academic_session"] != EXPECTED_ACADEMIC_SESSION:
            raise RuntimeError(
                f"Academic session mismatch.\n"
                f"Expected: {EXPECTED_ACADEMIC_SESSION}\n"
                f"Received: {r['academic_session']}"
            )

        class_code = r["class_code"]

        course_number = parse_course_number_from_class(class_code)
        instructional_type = parse_instructional_type_from_class(class_code)

        duration_minutes = coerce_duration(
            parse_duration_to_minutes(r["class_duration_raw"])
        )

        normalized.append({
            "academic_session": r["academic_session"],
            "week_begins": r["week_begins"],
            "subject_area": r["faculty"],
            "course_number": course_number,
            "class_code": class_code,
            "class_duration_raw": r["class_duration_raw"],
            "duration_minutes": duration_minutes,
            "duration_weeks": r["duration_weeks"],
            "instructional_type": instructional_type,
            "lecturer_code": r["lecturer_code"],
            "lecturer_name": r["lecturer_name"],
            "total_students": r["total_students"],
            "intakes": r["intakes"]
        })

    return normalized


def parse_instructional_type_from_class(class_code: str) -> str:
    if "-L-" in class_code:
        return "Lecture"
    if "-T-" in class_code:
        return "Tutorial"
    if "-P-" in class_code:
        return "Practical"
    return "Lecture"


def parse_course_number_from_class(class_code: str) -> str:
    """
    Example:
    SoMAQS___AAQS005-4-1-QM-L-1___2026-07-06

    We extract:
    AAQS005-4-1-QM
    """

    middle = class_code.split("___")[1]
    parts = middle.split("-")

    if len(parts) >= 2:
        return "-".join(parts[:-2])

    return middle


def group_records(records):
    grouped = defaultdict(lambda: {
        "subject_area": None,
        "course_number": None,
        "week_begins": None,
        "classes": []
    })

    for r in records:
        key = (
            r["subject_area"],
            r["course_number"],
            r["week_begins"]
        )

        group = grouped[key]

        group["subject_area"] = r["subject_area"]
        group["course_number"] = r["course_number"]
        group["week_begins"] = r["week_begins"]

        group["classes"].append(r)

    return list(grouped.values())