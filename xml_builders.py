from datetime import datetime
from config import EXPECTED_ACADEMIC_SESSION

def xml_escape(s: str) -> str:
    if s is None:
        return ""
    return (
        s.replace("&", "&amp;")
         .replace("<", "&lt;")
         .replace(">", "&gt;")
         .replace('"', "&quot;")
         .replace("'", "&apos;")
    )


def format_date(d: str) -> str:
    return datetime.strptime(d, "%d/%m/%Y").strftime("%Y-%m-%d")

# Time Patterns
def build_time_pattern_xml(name, start_times_hhmm):
    times_xml = "".join(
        f'<time start="{t}"/>' for t in start_times_hhmm
    )

    return f"""
<timePattern>
  <name>{xml_escape(name)}</name>
  <times>
    {times_xml}
  </times>
</timePattern>
"""

# Main XML Builder
def build_data_exchange_xml(grouped_records, time_patterns, existing_courses, existing_classes):
    instructors = {}
    offerings_xml = ""
    time_pattern_xml_blocks = []

    # Time Patterns
    for tp_name, starts in time_patterns.items():
        time_pattern_xml_blocks.append(
            build_time_pattern_xml(tp_name, starts)
        )

    # Instructional Offerings (Grouped)
    for group in grouped_records:
        subject_area = group["subject_area"]
        course_number = group["course_number"]
        classes = group["classes"]

        course_key = (subject_area, course_number)

        existing_course = existing_courses.get(course_key)
        config_name = "Default Config"

        config_action = "insert"

        if existing_course:
            if existing_course and config_name in existing_course.get("configurations", {}):
                config_action = "update"

        # Build class XML blocks
        class_blocks = ""

        for r in classes:

            # Register instructor (unique)
            instructors[r["lecturer_code"]] = f"""
<instructor>
  <externalId>{xml_escape(r["lecturer_code"])}</externalId>
  <name>{xml_escape(r["lecturer_name"])}</name>
</instructor>
"""

            external_id = r["class_code"]

            existing = existing_classes.get(external_id)

            action = "insert"

            if existing:
                # Compare fields
                if (
                        existing["limit"] != r["total_students"] or
                        existing["instructor"] != r["lecturer_code"] or
                        existing["weeks"] != r["duration_weeks"] or
                        existing["timePattern"] != r["time_pattern_name"]
                ):
                    action = "update"
                else:
                    print(f"Class unchanged: {external_id}")
                    continue  # Skip identical class

            class_blocks += f"""
            <class action="{action}">
              <externalId>{xml_escape(external_id)}</externalId>
              <instructionalType>{xml_escape(r["instructional_type"])}</instructionalType>
              <limit>{r["total_students"]}</limit>
              <weeks>{r["duration_weeks"]}</weeks>
              <timePattern>{xml_escape(r["time_pattern_name"])}</timePattern>
              <instructors>
                <instructor externalId="{xml_escape(r["lecturer_code"])}"/>
              </instructors>
            </class>
            """

        if not class_blocks.strip():
            continue

        # Determine offering action
        offering_action = "insert"
        if course_key in existing_courses:
            offering_action = "update"

        offerings_xml += f"""
        <instructionalOffering action="{offering_action}">
          <subject>{xml_escape(subject_area)}</subject>
          <courseNumber>{xml_escape(course_number)}</courseNumber>

          <configurations>
            <configuration action="{config_action}">
              <name>{config_name}</name>
              <classes>
                {class_blocks}
              </classes>
            </configuration>
          </configurations>

        </instructionalOffering>
        """

        if offering_action == "update":
            print(f"Updating existing course: {course_number}")
        else:
            print(f"Creating new course: {course_number}")

    # Assemble XML
    instructors_xml = "".join(instructors.values())
    session_xml = build_session_xml()
    curricula_xml = build_curricula_xml(grouped_records)

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<dataExchange>

{session_xml}

{curricula_xml}

<timePatterns>
  {''.join(time_pattern_xml_blocks)}
</timePatterns>

<instructors>
  {instructors_xml}
</instructors>

<instructionalOfferings>
  {offerings_xml}
</instructionalOfferings>

</dataExchange>
"""

def build_session_xml():
    year, term = EXPECTED_ACADEMIC_SESSION.split()
    return f"""
  <session>
    <academicYear>{year}</academicYear>
    <term>{term}</term>
  </session>
"""

def build_curricula_xml(records):
    curricula = {}

    for r in records:
        if "intakes" not in r or not r["intakes"]:
            continue

        for intake in r["intakes"]:
            key = intake["code"]

            curricula.setdefault(key, []).append({
                "subject": r["subject_area"],
                "course": r["course_number"],
                "students": intake["students"]
            })

    xml_blocks = []

    for intake_code, projections in curricula.items():
        projections_xml = ""

        for p in projections:
            projections_xml += f"""
        <courseProjection>
          <subject>{xml_escape(p["subject"])}</subject>
          <courseNumber>{xml_escape(p["course"])}</courseNumber>
          <students>{p["students"]}</students>
        </courseProjection>
"""

        xml_blocks.append(f"""
  <curriculum>
    <abbreviation>{xml_escape(intake_code)}</abbreviation>
    <name>{xml_escape(intake_code)}</name>
    <courseProjections>
      {projections_xml}
    </courseProjections>
  </curriculum>
""")

    return f"""
<curricula>
  {''.join(xml_blocks)}
</curricula>
"""