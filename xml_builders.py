from datetime import datetime
import zipfile
import os
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
import re

def parse_minutes_from_name(name: str, default: int = 120) -> int:
    """
    Parses the time pattern name for duration in hours and minutes.
    Examples:
      'Auto 1 H' -> 60
      'Auto 2 H 30 M' -> 150
      'Auto 2 H 15 M' -> 135
      'Auto 3 H' -> 180
    Returns default if not found.
    """
    pattern = r"(\d+)\s*H(?:\s*(\d+)\s*M)?"
    match = re.search(pattern, name, re.IGNORECASE)
    if match:
        hours = int(match.group(1))
        minutes = int(match.group(2)) if match.group(2) else 0
        return hours * 60 + minutes
    # Try just minutes
    pattern_min = r"(\d+)\s*M"
    match_min = re.search(pattern_min, name, re.IGNORECASE)
    if match_min:
        return int(match_min.group(1))
    return default

def build_time_pattern_xml(name, start_times_hhmm, nbr_meetings=1, mins_per_meeting=None):
    day_codes = ["M", "T", "W", "Th", "F"]
    days_xml = "".join([f'<days code="{d}"/>' for d in day_codes])

    if mins_per_meeting is None:
        mins_per_meeting = parse_minutes_from_name(name)

    """Returns a single time pattern block."""
    times_xml = "".join(
        f'<time start="{t}"/>' for t in start_times_hhmm
    )
    return f"""
    <timePattern name="{xml_escape(name)}" 
                 nbrMeetings="{nbr_meetings}" 
                 minsPerMeeting="{mins_per_meeting}" 
                 type="Standard" 
                 visible="true">
      {days_xml}
      {times_xml}
    </timePattern>"""

# Main XML Builder
def build_data_exchange_xml(grouped_records, flat_records, time_patterns, existing_courses, existing_classes):
    instructors = {}
    offerings_xml = ""
    time_pattern_xml_blocks = []
    year, term = EXPECTED_ACADEMIC_SESSION.split()

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
              <staff term="{term}" year="{year}" campus="APU">
                <employee externalId="{xml_escape(r["lecturer_code"])}"/>
              </staff>
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
    curricula_xml = build_curricula_xml(flat_records)

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

<offerings term="{term}" year="{year}" campus="APU" incremental="true">
  {offerings_xml}
</offerings>

</dataExchange>
"""

def build_session_xml():
    year, term = EXPECTED_ACADEMIC_SESSION.split()
    return f"""
  <academicSessionSetup type="base" term="{term}" year="{year}" campus="APU" incremental="true">
    <!-- Leave empty or add a comment -->
</academicSessionSetup>
"""

def build_curricula_xml(records):
    # Deduplicate projections: a curriculum (intake) may appear across multiple
    # class records for the same course; UniTime expects one projection per
    # (intake_code, subject, courseNumber).
    curricula = {}
    area_map = {}
    year, term = EXPECTED_ACADEMIC_SESSION.split()

    for r in records:
        intakes = r.get("intakes") or []
        if not intakes:
            continue

        subject = r["subject_area"]
        course = r["course_number"]
        # get area_abbreviation from record, fallback to None
        area_abbreviation = r.get("area_abbreviation")

        for intake in intakes:
            intake_code = intake["code"]
            students = intake.get("students", 0) or 0

            by_course = curricula.setdefault(intake_code, {})
            by_course[(subject, course)] = by_course.get((subject, course), 0) + students
            # Save area_abbreviation for this intake_code if present
            if area_abbreviation:
                area_map[intake_code] = area_abbreviation

    xml_blocks = []

    for intake_code, projections_map in curricula.items():
        projections_xml = ""

        for (subject, course), students in projections_map.items():
            projections_xml += f'<courseProjection subject="{xml_escape(subject)}" courseNumber="{xml_escape(course)}" students="{students}"/>'

        # Get area_abbreviation for this intake_code, default to 'Deg'
        area_abbr = area_map.get(intake_code, "Deg")
        xml_blocks.append(f'<curriculum academicArea="{xml_escape(area_abbr)}" abbreviation="{xml_escape(intake_code)}" name="{xml_escape(intake_code)}">'
                         f'<courseProjections>{projections_xml}</courseProjections>'
                         f'</curriculum>')

    return f'<curricula campus="APU" term="{term}" year="{year}">' + ''.join(xml_blocks) + '</curricula>'

def build_data_exchange_zip(grouped_records, flat_records, time_patterns, existing_courses, existing_classes, output_path=None):
    year, term = EXPECTED_ACADEMIC_SESSION.split()
    campus = "APU"

    # 1. Build Session XML
    session_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<sessionSetup term="{term}" year="{year}" campus="{campus}" incremental="true">
    <!-- Inner data goes here if needed -->
</sessionSetup>"""

    tp_blocks = "".join([build_time_pattern_xml(name, starts) for name, starts in time_patterns.items()])
    time_patterns_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<sessionSetup term="{term}" year="{year}" campus="{campus}" incremental="true">
    <timePatterns>
    {tp_blocks}
    </timePatterns>
</sessionSetup>"""

    # 2. Build Staff (Instructor) XML
    staff_entries = {}
    for group in grouped_records:
        for r in group["classes"]:
            code = str(r["lecturer_code"]).strip()
            name = str(r["lecturer_name"]).strip()
            if code.upper() == "TBA" or name.upper() == "TBA":
                continue
            if "." in name:
                first, last = name.split(".", 1)
                first = first.strip()
                last = last.strip()
            else:
                first = name
                last = name
            staff_entries[code] = f'<employee externalId="{xml_escape(code)}" firstName="{xml_escape(first)}" lastName="{xml_escape(last)}"/>'

    staff_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<staff term="{term}" year="{year}" campus="{campus}">
{"".join(staff_entries.values())}
</staff>"""

    # 3. Build Curricula XML
    # Note: Using your existing build_curricula_xml logic but ensuring it's standalone
    curricula_content = build_curricula_xml(flat_records)
    curricula_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
{curricula_content}"""

    # 4. Build Offerings XML
    offerings_body = ""
    for group in grouped_records:
        subject_area = group["subject_area"]
        course_number = group["course_number"]
        course_key = (subject_area, course_number)
        
        class_blocks = ""
        for r in group["classes"]:
            action = "update" if existing_classes.get(r["class_code"]) else "insert"
            
            class_blocks += f"""
            <class action="{action}" type="{xml_escape(r["instructional_type"])}" limit="{r["total_students"]}" externalId="{xml_escape(r["class_code"])}">
              <weeks>{r["duration_weeks"]}</weeks>
              <timePattern>{xml_escape(r["time_pattern_name"])}</timePattern>
              <instructor externalId="{xml_escape(r["lecturer_code"])}" responsibility="Teaching"/>
            </class>"""

        if not class_blocks.strip(): continue

        off_action = "update" if course_key in existing_courses else "insert"
        offerings_body += f"""
        <instructionalOffering action="{off_action}">
          <subject>{xml_escape(subject_area)}</subject>
          <courseNumber>{xml_escape(course_number)}</courseNumber>
          <configurations>
            <configuration action="insert" name="Default Config">
              <classes>{class_blocks}</classes>
            </configuration>
          </configurations>
        </instructionalOffering>"""

    offerings_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<offerings term="{term}" year="{year}" campus="{campus}" incremental="true">
{offerings_body}
</offerings>"""

    if not output_path:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = f"xml_snapshot_{timestamp}.zip"

    zip_path = create_unitime_zip_package(
        output_path,
        session_xml,
        time_patterns_xml,
        staff_xml,
        curricula_xml,
        offerings_xml,
    )

    return {
        "zip_path": zip_path,
        "sections": {
            "session": session_xml,
            "time_patterns": time_patterns_xml,
            "staff": staff_xml,
            "curricula": curricula_xml,
            "offerings": offerings_xml,
        },
    }

def create_unitime_zip_package(output_zip_path, session_xml, time_patterns_xml, staff_xml, curricula_xml, offerings_xml):
    """
    Creates a zip archive containing the four required UniTime XML files.
    """
    try:
        with zipfile.ZipFile(output_zip_path, 'w', zipfile.ZIP_DEFLATED) as unitime_zip:
            # Writing each individual XML string into its own file inside the zip
            unitime_zip.writestr("01_session.xml", session_xml)
            unitime_zip.writestr("02_time_patterns.xml", time_patterns_xml)
            unitime_zip.writestr("03_staff.xml", staff_xml)
            unitime_zip.writestr("04_curricula.xml", curricula_xml)
            unitime_zip.writestr("05_offerings.xml", offerings_xml)
            
        print(f"Successfully created: {output_zip_path}")
        return output_zip_path
    except Exception as e:
      print(f"Error creating zip: {e}")
      return None