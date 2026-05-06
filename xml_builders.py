from datetime import datetime
import csv
import os
import zipfile
from config import EXPECTED_ACADEMIC_SESSION
import re
from collections import defaultdict
import xml.etree.ElementTree as ET

TIME_PREFERENCE_DAYS = "MTWRF"
TIME_PREFERENCE_START_TIME = "0830"
TIME_PREFERENCE_END_TIME = "1800"
CLASS_START_DATE = "01/01"
CLASS_END_DATE = "12/31"

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

def class_suffix(record: dict) -> str:
    """
    UniTime requires a class suffix in course offering imports. Prefer the
    group number from type_and_number, falling back to the class_code tail.
    """
    type_and_number = str(record.get("type_and_number") or "")
    match = re.search(r"(?:^|-)(\d+[A-Za-z]*)$", type_and_number)
    if match:
        return match.group(1)

    class_code = str(record.get("class_code") or "")
    if "___" in class_code:
        class_part = class_code.split("___")[1]
        match = re.search(r"-(\d+[A-Za-z]*)$", class_part)
        if match:
            return match.group(1)

    return "1"

def instructional_type_from_class_code(class_code: str) -> str:
    """
    UniTime instructional type abbreviations required by this database.
    The class code is the source of truth for offerings import types.
    """
    code = str(class_code or "")
    if "-Lab-" in code:
        return "Lab"
    if "-T-" in code:
        return "T"
    if "-L-" in code:
        return "Lec"
    return "Lec"

def shortened_class_id(class_code: str, max_length: int = 40) -> str:
    """
    Builds a UniTime-safe class id from:
    [Subject]___[CourseNbr]-[Type]-[Suffix]___[YYYY-MM-DD]
    into:
    [Subject]_[CourseCode]-[Type][Suffix]_[YY-MM-DD]
    """
    code = str(class_code or "").strip()
    parts = code.split("___")

    if len(parts) >= 3:
        subject = parts[0].strip()
        class_part = parts[1].strip()
        date_part = parts[2].strip()

        date_match = re.match(r"(\d{2})?(\d{2}-\d{2}-\d{2})$", date_part)
        short_date = date_match.group(2) if date_match else date_part

        class_match = re.match(r"(.+?)-(Lab|L|T)-(.+)$", class_part)
        if class_match:
            course_core, instr_type, suffix = class_match.groups()
            course_code = course_core.split("-", 1)[0]
            new_id = f"{subject}_{course_code}-{instr_type}{suffix}_{short_date}"
        else:
            new_id = f"{subject}_{class_part}_{short_date}"
    else:
        new_id = code.replace("___", "_")
        new_id = re.sub(r"_(\d{2})?(\d{2}-\d{2}-\d{2})$", r"_\2", new_id)

    if len(new_id) > max_length:
        raise ValueError(
            f"Generated class id exceeds {max_length} characters: {new_id} "
            f"from source class_code {code}"
        )

    return new_id

def time_preference_xml() -> str:
    return (
        f'<time days="{TIME_PREFERENCE_DAYS}" '
        f'startTime="{TIME_PREFERENCE_START_TIME}" '
        f'endTime="{TIME_PREFERENCE_END_TIME}" '
        f'preference="1"/>'
    )

def class_date_xml() -> str:
    return f'<date startDate="{CLASS_START_DATE}" endDate="{CLASS_END_DATE}"/>'

def subject_area_from_class_code(class_code: str) -> str | None:
    """
    Parses [Cluster]___[ModulePrefix][Numbers]... into "[ModulePrefix] [Cluster]".
    Example: MHR___BM004-3-1-BCS-L-1___2026-03-16 -> BM MHR.
    """
    if not class_code or "___" not in class_code:
        return None

    cluster, remainder = class_code.split("___", 1)
    cluster = cluster.strip()
    module_part = remainder.split("___", 1)[0].strip()
    module_prefix_match = re.match(r"([A-Za-z]+)", module_part)

    if not cluster or not module_prefix_match:
        return None

    module_prefix = module_prefix_match.group(1).strip()
    if not module_prefix:
        return None

    return f"{module_prefix} {cluster}"

def load_valid_subject_areas(csv_path: str | None = None) -> dict[str, str]:
    if csv_path is None:
        csv_path = os.path.join(os.path.dirname(__file__), "subjectArea.csv")

    valid_subject_areas = {}
    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        for row in reader:
            if not row:
                continue

            subject_area = row[0].strip()
            if not subject_area or subject_area.lower() == "abbv":
                continue

            valid_subject_areas[subject_area.upper()] = subject_area

    return valid_subject_areas

def log_class_without_subject_area(group: dict, record: dict, reason: str, parsed_subject_area: str | None = None):
    log_dir = os.path.join(os.path.dirname(__file__), "Class codes without subject areas")
    os.makedirs(log_dir, exist_ok=True)

    class_code = str(record.get("class_code") or "unknown")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"class_without_subject_area_{class_code}_{timestamp}.txt"
    filepath = os.path.join(log_dir, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f"reason: {reason}\n")
        f.write(f"parsed_subject_area: {parsed_subject_area or ''}\n\n")

        f.write("=== OFFERING ===\n")
        for k, v in group.items():
            if k != "classes":
                f.write(f"{k}: {v}\n")

        f.write("\n=== CLASS ===\n")
        for k, v in record.items():
            f.write(f"{k}: {v}\n")

def validate_offerings_xml(xml_text: str):
    root = ET.fromstring(xml_text)
    if root.tag != "offerings":
        raise ValueError("Offerings XML root must be <offerings>.")

    for offering in root.findall("offering"):
        if not offering.get("offered"):
            raise ValueError(f"Offering {offering.get('id')} is missing required offered attribute.")

        for cls in offering.findall(".//class"):
            if not cls.get("suffix"):
                raise ValueError(f"Class {cls.get('id')} is missing required suffix attribute.")
            if len(cls.get("id", "")) > 40:
                raise ValueError(f"Class id exceeds 40 characters: {cls.get('id')}")
            if "datePattern" in cls.attrib:
                raise ValueError(f"Class {cls.get('id')} uses obsolete datePattern attribute.")

            date_pref = cls.find("date")
            if date_pref is None:
                raise ValueError(f"Class {cls.get('id')} is missing required date element.")
            if date_pref.get("startDate") != CLASS_START_DATE:
                raise ValueError(f"Class {cls.get('id')} has invalid date startDate.")
            if date_pref.get("endDate") != CLASS_END_DATE:
                raise ValueError(f"Class {cls.get('id')} has invalid date endDate.")

            time_pref = cls.find("time")
            if time_pref is None:
                raise ValueError(f"Class {cls.get('id')} is missing required time preference.")
            if "start" in time_pref.attrib or "pattern" in time_pref.attrib:
                raise ValueError(f"Class {cls.get('id')} uses obsolete bitmask time attributes.")
            if time_pref.get("days") != TIME_PREFERENCE_DAYS:
                raise ValueError(f"Class {cls.get('id')} has invalid time preference days.")
            if time_pref.get("startTime") != TIME_PREFERENCE_START_TIME:
                raise ValueError(f"Class {cls.get('id')} has invalid time preference startTime.")
            if time_pref.get("endTime") != TIME_PREFERENCE_END_TIME:
                raise ValueError(f"Class {cls.get('id')} has invalid time preference endTime.")
            if time_pref.get("preference") != "1":
                raise ValueError(f"Class {cls.get('id')} has invalid time preference value.")

        for subpart in offering.findall(".//subpart"):
            if subpart.findall("class"):
                raise ValueError(
                    f"Offering {offering.get('id')} has class elements nested inside subpart elements."
                )

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
# def build_data_exchange_xml(grouped_records, flat_records, time_patterns, existing_courses, existing_classes):
#     instructors = {}
#     offerings_xml = ""
#     time_pattern_xml_blocks = []
#     year, term = EXPECTED_ACADEMIC_SESSION.split()
#
#     # Time Patterns
#     for tp_name, starts in time_patterns.items():
#         time_pattern_xml_blocks.append(
#             build_time_pattern_xml(tp_name, starts)
#         )
#
#     # Instructional Offerings (Grouped)
#     for group in grouped_records:
#         subject_area = group["subject_area"]
#         course_number = group["course_number"]
#         classes = group["classes"]
#
#         course_key = (subject_area, course_number)
#
#         existing_course = existing_courses.get(course_key)
#         config_name = "Default Config"
#
#         config_action = "insert"
#
#         if existing_course:
#             if existing_course and config_name in existing_course.get("configurations", {}):
#                 config_action = "update"
#
#         # Build class XML blocks
#         class_blocks = ""
#
#         for r in classes:
#
#             # Register instructor (unique)
#             instructors[r["lecturer_code"]] = f"""
# <instructor>
#   <externalId>{xml_escape(r["lecturer_code"])}</externalId>
#   <name>{xml_escape(r["lecturer_name"])}</name>
# </instructor>
# """
#
#             external_id = r["class_code"]
#
#             existing = existing_classes.get(external_id)
#
#             action = "insert"
#
#             if existing:
#                 # Compare fields
#                 if (
#                         existing["limit"] != r["total_students"] or
#                         existing["instructor"] != r["lecturer_code"] or
#                         existing["weeks"] != r["duration_weeks"] or
#                         existing["timePattern"] != r["time_pattern_name"]
#                 ):
#                     action = "update"
#                 else:
#                     print(f"Class unchanged: {external_id}")
#                     continue  # Skip identical class
#
#             class_blocks += f"""
#             <class action="{action}">
#               <externalId>{xml_escape(external_id)}</externalId>
#               <instructionalType>{xml_escape(r["instructional_type"])}</instructionalType>
#               <limit>{r["total_students"]}</limit>
#               <weeks>{r["duration_weeks"]}</weeks>
#               <timePattern>{xml_escape(r["time_pattern_name"])}</timePattern>
#               <staff term="{term}" year="{year}" campus="APU">
#                 <employee externalId="{xml_escape(r["lecturer_code"])}"/>
#               </staff>
#             </class>
#             """
#
#         if not class_blocks.strip():
#             continue
#
#         # Determine offering action
#         offering_action = "insert"
#         if course_key in existing_courses:
#             offering_action = "update"
#
#         offerings_xml += f"""
#         <instructionalOffering action="{offering_action}">
#           <subject>{xml_escape(subject_area)}</subject>
#           <courseNumber>{xml_escape(course_number)}</courseNumber>
#
#           <configurations>
#             <configuration action="{config_action}">
#               <name>{config_name}</name>
#               <classes>
#                 {class_blocks}
#               </classes>
#             </configuration>
#           </configurations>
#
#         </instructionalOffering>
#         """
#
#         if offering_action == "update":
#             print(f"Updating existing course: {course_number}")
#         else:
#             print(f"Creating new course: {course_number}")
#
#     # Assemble XML
#     instructors_xml = "".join(instructors.values())
#     session_xml = build_session_xml()
#     curricula_xml = build_curricula_xml(flat_records)
#
#     return f"""<?xml version="1.0" encoding="UTF-8"?>
# <dataExchange>
#
# {session_xml}
#
# {curricula_xml}
#
# <timePatterns>
#   {''.join(time_pattern_xml_blocks)}
# </timePatterns>
#
# <instructors>
#   {instructors_xml}
# </instructors>
#
# <offerings term="{term}" year="{year}" campus="APU" incremental="true">
#   {offerings_xml}
# </offerings>
#
# </dataExchange>
# """

def build_session_xml():
    year, term = EXPECTED_ACADEMIC_SESSION.split()
    return f"""
  <academicSessionSetup type="base" term="{term}" year="{year}" campus="{year}" incremental="true">
    <!-- Leave empty or add a comment -->
</academicSessionSetup>
"""

def map_academic_area_abbreviation(intake_code: str) -> str:
    """
    Maps the major code prefix to the academic area abbreviation.

    Mapping:
    - "AFC" → "Cert"
    - "UCD" → "Dip"
    - "APUM" → "Mas"
    - "APUP" → "PhD"
    - Otherwise → "Deg" (Default)
    """
    prefix = str(intake_code or "").upper()

    if prefix.startswith("AFC"):
        return "Cert"
    elif prefix.startswith("UCD"):
        return "Dip"
    elif prefix.startswith("APUM"):
        return "Mas"
    elif prefix.startswith("APUP"):
        return "PhD"
    else:
        return "Deg"

def map_academic_area_long_name(abbreviation: str) -> str:
    """
    Maps the academic area abbreviation to its long name.

    Mapping:
    - "Cert" → "Certification"
    - "Dip" → "Diploma"
    - "Mas" → "Masters"
    - "PhD" → "Doctor of Philosophy"
    - "Deg" → "Degree" (Default)
    """
    mapping = {
        "Cert": "Certification",
        "Dip": "Diploma",
        "Mas": "Masters",
        "PhD": "Doctor of Philosophy",
        "Deg": "Degree"
    }
    return mapping.get(abbreviation, "Degree")

def build_curricula_xml(records):
    # Load valid subject areas to match offerings logic
    valid_subject_areas = load_valid_subject_areas()

    curricula = defaultdict(lambda: defaultdict(list))
    year, term = EXPECTED_ACADEMIC_SESSION.split()
    campus = year

    # Group records by (intake_code, subject_area) to match offerings logic
    for r in records:
        intakes = r.get("intakes") or []
        for intake in intakes:
            intake_code = intake["code"]

            # Extract subject_area from class_code, same as offerings XML
            parsed_subject_area = subject_area_from_class_code(r.get("class_code"))
            if not parsed_subject_area:
                continue

            canonical_subject_area = valid_subject_areas.get(parsed_subject_area.upper())
            if not canonical_subject_area:
                continue

            # Group by (intake_code, canonical subject area)
            curricula[intake_code][canonical_subject_area].append(r)

    xml_blocks = []
    for intake_code, subject_groups in sorted(curricula.items()):
        if not subject_groups:
            continue

        # Find department (from first class_code)
        dept = None
        for r in list(subject_groups.values())[0]:
            class_code_val = r.get("class_code", "")
            if class_code_val:
                dept = class_code_val.split("___")[0]
                break
        if not dept:
            dept = "UNK"

        # Build classifications across all subject areas within this major
        classifications = defaultdict(lambda: {"courses": set(), "enrollment": 0})

        for subject_area, records_list in subject_groups.items():
            for r in records_list:
                type_and_number = r.get("type_and_number") or ""
                match = re.search(r"L-(\d+)", str(type_and_number))
                if match:
                    group_num = match.group(1)
                    class_code = f"G{group_num}"
                else:
                    class_code = "G1"

                # Use subject_area and course_number (full), same as offerings
                course_nbr = r.get("course_number", "")
                classifications[class_code]["courses"].add((subject_area, course_nbr))

                # Add enrollment
                try:
                    n_students = int(r.get("total_students", 0))
                except Exception:
                    n_students = 0
                classifications[class_code]["enrollment"] += n_students

        # Build <classification> blocks
        classification_blocks = ""
        for class_code, data in sorted(classifications.items()):
            enrollment = data["enrollment"]
            courses = data["courses"]
            classification_blocks += f'<classification enrollment="{enrollment}">'
            classification_blocks += f'<academicClassification code="{xml_escape(class_code)}"/>'
            for subject, course_nbr in sorted(courses):
                classification_blocks += f'<course subject="{xml_escape(subject)}" courseNbr="{xml_escape(course_nbr)}"/>'
            classification_blocks += f'</classification>'

        # Determine academic area abbreviation and long name based on major code prefix
        academic_area_abbr = map_academic_area_abbreviation(intake_code)
        academic_area_long_name = map_academic_area_long_name(academic_area_abbr)

        # Create curriculum abbreviation and name attributes
        curriculum_abbreviation = f"{academic_area_abbr}/{intake_code}"
        curriculum_name = f"{academic_area_long_name} / {intake_code}"

        # Build curriculum with flat hierarchy for academicArea, department, and major
        xml_blocks.append(
            f'<curriculum abbreviation="{xml_escape(curriculum_abbreviation)}" '
            f'name="{xml_escape(curriculum_name)}">'
            f'<academicArea abbreviation="{academic_area_abbr}"/>'
            f'<department code="{xml_escape(dept.upper())}"/>'
            f'<major code="{xml_escape(intake_code)}"/>'
            f'{classification_blocks}'
            f'</curriculum>'
        )

    return f'<curricula campus="{xml_escape(campus)}" term="{xml_escape(term)}" year="{xml_escape(year)}">' + ''.join(xml_blocks) + '</curricula>'

def build_data_exchange_zip(grouped_records, flat_records, time_patterns, existing_courses, existing_classes, output_path=None):
    year, term = EXPECTED_ACADEMIC_SESSION.split()
    campus = year

    # 1. Build Session XML
    session_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
    <!DOCTYPE sessionSetup PUBLIC "-//UniTime//UniTime Academic Session Setup/EN" "http://www.unitime.org/interface/AcademicSessionSetup.dtd">
<sessionSetup term="{term}" year="{year}" campus="{campus}" incremental="true">
    <!-- Inner data goes here if needed -->
</sessionSetup>"""

    tp_blocks = "".join([build_time_pattern_xml(name, starts) for name, starts in time_patterns.items()])
    time_patterns_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
    <!DOCTYPE sessionSetup PUBLIC "-//UniTime//UniTime Academic Session Setup/EN" "http://www.unitime.org/interface/AcademicSessionSetup.dtd">
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
    <!DOCTYPE staff PUBLIC "-//UniTime//DTD University Course Timetabling/EN" "http://www.unitime.org/interface/Staff.dtd">
<staff term="{term}" year="{year}" campus="{campus}">
{"".join(staff_entries.values())}
</staff>"""

    # 3. Build Curricula XML
    # Note: Using your existing build_curricula_xml logic but ensuring it's standalone
    curricula_content = build_curricula_xml(flat_records)
    curricula_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
    <!DOCTYPE curricula PUBLIC "-//UniTime//DTD University Course Timetabling/EN" "http://www.unitime.org/interface/Curricula_3_2.dtd">
{curricula_content}"""

    # 4. Build Offerings XML
    offerings_body = ""
    valid_subject_areas = load_valid_subject_areas()

    for group in grouped_records:
        course_number = group["course_number"]

        classes_by_subject_area = defaultdict(list)
        for r in group["classes"]:
            parsed_subject_area = subject_area_from_class_code(r.get("class_code"))
            if not parsed_subject_area:
                log_class_without_subject_area(
                    group,
                    r,
                    reason="Class code could not be parsed into a subject area."
                )
                continue

            canonical_subject_area = valid_subject_areas.get(parsed_subject_area.upper())
            if not canonical_subject_area:
                log_class_without_subject_area(
                    group,
                    r,
                    reason="Parsed subject area was not found in subjectArea.csv.",
                    parsed_subject_area=parsed_subject_area
                )
                continue

            classes_by_subject_area[canonical_subject_area].append(r)

        if not classes_by_subject_area:
            continue

        for subject_area, valid_classes in sorted(classes_by_subject_area.items()):
            course_key = (subject_area, course_number)

            # Group classes by UniTime instructional type abbreviation.
            subparts_dict = defaultdict(list)
            total_limit = 0
            for r in valid_classes:
                instr_type = instructional_type_from_class_code(r.get("class_code"))
                subparts_dict[instr_type].append(r)
                try:
                    total_limit += int(r.get("total_students", 0))
                except Exception:
                    pass

            if not subparts_dict:
                continue

            # Build subpart definitions and class records as siblings under config.
            subparts_xml = ""
            classes_xml = ""
            for instr_type, classes in sorted(subparts_dict.items()):
                # Calculate minPerWeek from time pattern (e.g., "Auto 2 H 30 M" -> 150)
                min_per_week = 120  # default
                if classes:
                    first_class = classes[0]
                    time_pattern_name = first_class.get("time_pattern_name", "")
                    min_per_week = parse_minutes_from_name(time_pattern_name)

                subparts_xml += f'<subpart type="{xml_escape(instr_type)}" suffix="" minPerWeek="{min_per_week}"/>'

                for r in classes:
                    instructor_xml = ""
                    class_id = shortened_class_id(r["class_code"])
                    date_xml = class_date_xml()
                    time_xml = time_preference_xml()
                    lecturer_code = str(r.get("lecturer_code") or "").strip()
                    if lecturer_code and lecturer_code.upper() != "TBA":
                        instructor_xml = (
                            f'<instructor id="{xml_escape(lecturer_code)}" '
                            f'share="1.0" lead="true"/>'
                        )
                    classes_xml += (
                        f'<class id="{xml_escape(class_id)}" '
                        f'type="{xml_escape(instr_type)}" '
                        f'suffix="{xml_escape(class_suffix(r))}" '
                        # f'limit="{r["total_students"]}">'
                        f'limit="{total_limit}">'
                        f'{date_xml}'
                        f'{instructor_xml}'
                        f'{time_xml}'
                        f'</class>'
                    )

            off_action = "update" if course_key in existing_courses else "insert"
            offering_id = course_number  # Use course_number as the ID
            offerings_body += f"""
        <offering id="{xml_escape(offering_id)}" offered="true" action="{off_action}">
          <course subject="{xml_escape(subject_area)}" courseNbr="{xml_escape(course_number)}" controlling="true" title=""/>
          <config name="Default Config" limit="{total_limit}">
            {subparts_xml}
            {classes_xml}
          </config>
        </offering>"""

    offerings_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE offerings PUBLIC "-//UniTime//DTD University Course Timetabling/EN" "http://www.unitime.org/interface/CourseOfferingExport.dtd">
<offerings term="{term}" year="{year}" campus="{campus}" incremental="true">
{offerings_body}
</offerings>"""

    validate_offerings_xml(offerings_xml)

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
            unitime_zip.writestr("04_offerings.xml", offerings_xml)
            unitime_zip.writestr("05_curricula.xml", curricula_xml)

            
        print(f"Successfully created: {output_zip_path}")
        return output_zip_path
    except Exception as e:
      print(f"Error creating zip: {e}")
      return None
