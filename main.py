from excel_loader import load_excel
from validators import validate_row, parse_duration
from xml_builders import (
    build_instructor_xml,
    build_course_xml,
    build_class_xml
)
from unitime_client import post_xml
from config import TIME_PATTERNS
from datetime import datetime

def main():
    df = load_excel("input.xlsx")

    instructors = {}
    courses = set()
    classes = []

    for _, row in df.iterrows():
        row = row.to_dict()

        duration_minutes = validate_row(row)

        # Instructor
        instructors[row["Lecturer Code"]] = row["Lecturer Name"]

        # Course parsing (AQ001-3-M-AIS-L-1)
        course_code = row["Subjects"].split("-")[0]
        subject_area = row["Subjects"].split("-")[3]

        courses.add((subject_area, course_code))

        # Date pattern code (must exist or be pre-generated)
        week_start = datetime.strptime(row["Week Begins"], "%d/%m/%Y")
        weeks = int(row["Duration (weeks)"])
        date_pattern_code = f"W{weeks}_{week_start.strftime('%Y%m%d')}"

        classes.append({
            "external_id": row["Class Code"],
            "course_nbr": course_code,
            "capacity": int(row["Total Students"]),
            "instructor": row["Lecturer Code"],
            "time_pattern": TIME_PATTERNS[duration_minutes],
            "date_pattern": date_pattern_code
        })

    # 1. Instructors
    print("Importing instructors...")
    post_xml(build_instructor_xml(instructors))

    # 2. Courses
    print("Importing course offerings...")
    post_xml(build_course_xml(courses))

    # 3. Classes
    print("Importing classes...")
    post_xml(build_class_xml(classes))

    print("Import completed successfully.")


if __name__ == "__main__":
    main()