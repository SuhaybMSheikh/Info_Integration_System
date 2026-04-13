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

        course_number = parse_course_number_from_class(
            r.get("module_code") or class_code
        )
        instructional_type = parse_instructional_type_from_class(
            r.get("type_and_number") or class_code
        )

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


def parse_instructional_type_from_class(value: str) -> str:
    if not value:
        return "Lecture"
    if "___" in value:
        if "-L-" in value:
            return "Lecture"
        if "-T-" in value:
            return "Tutorial"
        if "-P-" in value:
            return "Practical"
        if "Lab" in value or "-Lab-" in value:
            return "Lab"
        return "Lecture"
    # API type_and_number: "{instructional_type}-{group_number}" e.g. L-1, Lab-T-2
    if "Lab-T" in value:
        return "Tutorial"
    if "L-T" in value:
        return "Tutorial"
    if "Lab" in value:
        return "Lab"
    if "T" in value:
        return "Tutorial"
    if "L" in value:
        return "Lecture"
    return "Lecture"


def parse_course_number_from_class(code_or_module: str) -> str:
    """
    New API: pass module_code directly (already formatted); returned unchanged.

    Legacy class code: e.g. SoMAQS___AAQS005-4-1-QM-L-1___2026-07-06
    extracts AAQS005-4-1-QM from the middle segment.
    """
    if "___" not in code_or_module:
        return code_or_module

    middle = code_or_module.split("___")[1]
    parts = middle.split("-")

    if len(parts) >= 2:
        return "-".join(parts[:-2])

    return middle


def group_records(records):
    grouped = {}
    for r in records:
        key = (
            r["subject_area"],
            r["course_number"],
            r["week_begins"]
        )
        if key not in grouped:
            grouped[key] = {
                "subject_area": r["subject_area"],
                "course_number": r["course_number"],
                "week_begins": r["week_begins"],
                "classes": []
            }
        grouped[key]["classes"].append(r)
    return list(grouped.values())

def filter_duplicates_by_class_code(records):
    seen = set()
    filtered = []
    duplicates = []
    for r in records:
        code = r["class_code"]
        if code in seen:
            duplicates.append(r)
        else:
            filtered.append(r)
            seen.add(code)
    return filtered, duplicates
