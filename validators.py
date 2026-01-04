from datetime import datetime
from config import TIME_PATTERNS

def parse_duration(duration_str: str) -> int:
    # Example: "1H 30M"
    hours = 0
    minutes = 0

    duration_str = duration_str.upper()

    if "H" in duration_str:
        hours = int(duration_str.split("H")[0].strip())

    if "M" in duration_str:
        minutes = int(duration_str.split("M")[0].split()[-1])

    return hours * 60 + minutes


def validate_row(row: dict):
    required = [
        "Subjects",
        "Lecturer Code",
        "Class Duration",
        "Total Students",
        "Class Code",
        "Week Begins",
        "Duration (weeks)"
    ]

    for field in required:
        if not row.get(field):
            raise ValueError(f"Missing required field: {field}")

    duration_minutes = parse_duration(row["Class Duration"])

    if duration_minutes not in TIME_PATTERNS:
        raise ValueError(f"No matching UniTime time pattern for {duration_minutes} minutes")

    try:
        datetime.strptime(str(row["Week Begins"]), "%d/%m/%Y")
    except ValueError:
        raise ValueError("Week Begins must be DD/MM/YYYY")

    if int(row["Total Students"]) <= 0:
        raise ValueError("Total Students must be > 0")

    return duration_minutes