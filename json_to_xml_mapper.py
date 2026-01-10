from xml_builders import (
    build_instructor_xml,
    build_course_xml,
    build_class_xml
)
from config import TIME_PATTERNS

def json_to_xml_payloads(data: dict):
    instructors_xml = build_instructor_xml(data["instructors"])

    courses = set()
    classes = []

    for module in data["modules"]:
        courses.add((module["subjectArea"], module["courseCode"]))

        for io in module["instructionalOfferings"]:
            cls = io["class"]
            classes.append({
                "external_id": cls["classCode"],
                "course_nbr": module["courseCode"],
                "capacity": cls["expectedStudents"],
                "instructor": cls["instructor"],
                "time_pattern": TIME_PATTERNS[cls["durationMinutes"]],
                "date_pattern": f"W{cls['weeks']}_{cls['weekBegins'].replace('/', '')}"
            })

    return {
        "instructors": instructors_xml,
        "courses": build_course_xml(courses),
        "classes": build_class_xml(classes)
    }
