from datetime import datetime

def format_date(date_obj) -> str:
    """
    Converts a datetime/date/string into UniTime date format (yyyy-MM-dd)
    """
    if isinstance(date_obj, str):
        # Expecting dd/MM/yyyy from Excel
        return datetime.strptime(date_obj, "%d/%m/%Y").strftime("%Y-%m-%d")

    return date_obj.strftime("%Y-%m-%d")

def xml_escape(text: str) -> str:
    """
    Minimal XML escaping
    """
    return (
        text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&apos;")
    )

def build_time_pattern_xml(
    duration_minutes: int,
    pattern_name: str,
    start_times: list[str],
    break_minutes: int = 15
) -> str:
    """
    Builds a UniTime timePattern element.
    Time patterns are resolved by NAME in Data Exchange.
    """

    times_xml = "\n".join(
        f'            <time start="{t}" />'
        for t in start_times
    )

    return f"""
    <timePattern>
        <name>{xml_escape(pattern_name)}</name>
        <minutes>{duration_minutes}</minutes>
        <breakTime>{break_minutes}</breakTime>
        <times>
{times_xml}
        </times>
    </timePattern>
    """

def build_instructor_xml(record: dict) -> str:
    """
    Builds instructor definition.
    UniTime will ignore duplicates based on externalId.
    """

    return f"""
    <instructor>
        <externalId>{xml_escape(record["lecturer_code"])}</externalId>
        <firstName>{xml_escape(record["lecturer_name"])}</firstName>
        <lastName>{xml_escape(record["lecturer_name"])}</lastName>
    </instructor>
    """

def build_class_xml(record: dict) -> str:
    """
    Builds a single class inside an instructional offering.
    """

    return f"""
        <class>
            <externalId>{xml_escape(record["class_code"])}</externalId>
            <limit>{record["total_students"]}</limit>
            <timePattern>{xml_escape(record["time_pattern_name"])}</timePattern>
            <instructor>{xml_escape(record["lecturer_code"])}</instructor>
        </class>
    """

def build_instructional_offering_xml(subject_code: str, faculty: str, classes_xml: str) -> str:
    """
    One instructional offering per subject per faculty.
    """

    return f"""
    <instructionalOffering>
        <subject>{xml_escape(faculty)}</subject>
        <courseNumber>{xml_escape(subject_code)}</courseNumber>
        <classes>
{classes_xml}
        </classes>
    </instructionalOffering>
    """

def build_instructional_offerings_xml(records: list[dict]) -> str:
    """
    Builds a full UniTime Data Exchange XML payload.

    Expected record keys:
    - subject
    - faculty
    - class_code
    - lecturer_name
    - lecturer_code
    - total_students
    - time_pattern_name
    """

    instructors_seen = set()
    instructors_xml = []

    offerings = {}

    for r in records:
        # Instructors (deduplicated)
        if r["lecturer_code"] not in instructors_seen:
            instructors_seen.add(r["lecturer_code"])
            instructors_xml.append(build_instructor_xml(r))

        # Group classes by (faculty, subject)
        key = (r["faculty"], r["subject"])
        offerings.setdefault(key, []).append(build_class_xml(r))

    offerings_xml = []
    for (faculty, subject), classes in offerings.items():
        offerings_xml.append(
            build_instructional_offering_xml(
                subject_code=subject,
                faculty=faculty,
                classes_xml="".join(classes)
            )
        )

    return f"""<?xml version="1.0" encoding="UTF-8"?>
    <dataExchange>
        <instructors>
    {''.join(instructors_xml)}
        </instructors>
    
        <instructionalOfferings>
    {''.join(offerings_xml)}
        </instructionalOfferings>
    </dataExchange>
    """