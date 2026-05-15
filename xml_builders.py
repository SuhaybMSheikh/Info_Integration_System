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
CLASS_START_DATE = "1/1"
CLASS_END_DATE = "12/31"
RESERVATION_CONFIG_ID = "Default Config"
RESERVATION_CLASSIFICATION = "G1"
INTAKE_SESSION_TO_CONFIG_DATE = {
    "2505": "25-06-16",
    "2508": "25-09-29",
    "2509": "25-09-29",
    "2512": "26-01-26",
    "2601": "26-01-26",
    "2603": "26-03-09",
    "2604": "26-04-27",
    "2605": "26-05-18",
    "2606": "26-06-15",
    "2607": "26-07-06",
    "2608": "26-08-17",
    "2609": "26-09-07",
    "2610": "26-10-12",
    "2611": "26-11-09",
    "2612": "26-12-07",
}
OFFERINGS_DOCTYPE = '<!DOCTYPE offerings PUBLIC "-//UniTime//DTD University Course Timetabling/EN" "http://www.unitime.org/interface/CourseOfferingExport.dtd">'
CLASS_DATE_FROM_ID_RE = re.compile(r"_(\d{2}-\d{2}-\d{2})$")
CLASS_TYPE_SORT_ORDER = {
    "Lec": 0,
    "T": 1,
    "Lab": 2,
}
INTAKE_PREFIX_TO_AREA = {
    "APD1F": "Deg",
    "APD2F": "Deg",
    "APD3F": "Deg",
    "APD4F": "Deg",
    "APU1F": "Deg",
    "APU2F": "Deg",
    "APU3F": "Deg",
    "APU4F": "Deg",
    "UCDF": "Dip",
    "UCD2F": "Dip",
    "UCFF": "Fou",
    "APUMF": "Mas",
    "APDMF": "Mas",
    "AFCF": "Cert",
}

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

def get_academic_area(intake_code: str) -> str:
    code = str(intake_code or "").strip().upper()
    for prefix in sorted(INTAKE_PREFIX_TO_AREA.keys(), key=len, reverse=True):
        if code.startswith(prefix):
            return INTAKE_PREFIX_TO_AREA[prefix]
    raise ValueError(f"Unknown intake prefix for code: {intake_code}")

def intake_session_code(intake_code: str) -> str:
    code = str(intake_code or "").strip().upper()
    for prefix in sorted(INTAKE_PREFIX_TO_AREA.keys(), key=len, reverse=True):
        if code.startswith(prefix):
            remainder = code[len(prefix):]
            match = re.match(r"(\d{4})", remainder)
            if match:
                return match.group(1)
            break

    match = re.search(r"(\d{4})", code)
    if match:
        return match.group(1)

    raise ValueError(f"Unable to extract intake session code from major: {intake_code}")

def reservation_config_name(intake_code: str, available_config_dates: set[str] | None = None) -> str:
    session_code = intake_session_code(intake_code)
    yy_mm = f"{session_code[:2]}-{session_code[2:]}"

    if available_config_dates:
        matching_dates = sorted(
            date for date in available_config_dates
            if date.startswith(f"{yy_mm}-")
        )
        if matching_dates:
            return f"Config {matching_dates[0]}"

    config_date = INTAKE_SESSION_TO_CONFIG_DATE.get(session_code)
    if not config_date:
        raise ValueError(
            f"No configuration date mapping found for intake session {session_code} "
            f"from major {intake_code}"
        )

    return f"Config {config_date}"


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

def clone_xml_element(element: ET.Element) -> ET.Element:
    return ET.fromstring(ET.tostring(element, encoding="unicode"))

def class_date_from_id(class_id: str) -> str:
    match = CLASS_DATE_FROM_ID_RE.search(str(class_id or ""))
    if not match:
        raise ValueError(f"Class id does not end with a YY-MM-DD date stamp: {class_id}")
    return match.group(1)

def class_sort_key(cls: ET.Element):
    class_type = cls.get("type", "")
    suffix = cls.get("suffix", "")
    suffix_match = re.search(r"\d+", suffix)
    suffix_number = int(suffix_match.group(0)) if suffix_match else 0
    return (
        CLASS_TYPE_SORT_ORDER.get(class_type, 99),
        suffix_number,
        suffix,
        cls.get("id", ""),
    )

def config_limit_from_classes(classes: list[ET.Element]) -> int:
    limits = []
    for cls in classes:
        try:
            limits.append(int(cls.get("limit", "0") or 0))
        except Exception:
            limits.append(0)
    return max(limits) if limits else 0

def split_offering_configs_by_class_date(offerings_xml: str) -> str:
    root = ET.fromstring(offerings_xml)

    for offering in root.findall("offering"):
        original_configs = list(offering.findall("config"))
        if not original_configs:
            continue

        subparts = []
        classes_by_date = defaultdict(list)

        for config in original_configs:
            subparts.extend(list(config.findall("subpart")))
            for cls in config.findall("class"):
                class_date = class_date_from_id(cls.get("id"))
                classes_by_date[class_date].append(cls)

        if not classes_by_date:
            continue

        for config in original_configs:
            offering.remove(config)

        for class_date in sorted(classes_by_date):
            classes = sorted(classes_by_date[class_date], key=class_sort_key)
            new_config = ET.Element(
                "config",
                {
                    "name": f"Config {class_date}",
                    "limit": str(config_limit_from_classes(classes)),
                }
            )

            for subpart in subparts:
                new_config.append(clone_xml_element(subpart))
            for cls in classes:
                new_config.append(clone_xml_element(cls))

            offering.append(new_config)

    ET.indent(root, space="  ")
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'{OFFERINGS_DOCTYPE}\n'
        f'{ET.tostring(root, encoding="unicode")}'
    )

def update_reservation_configurations(
    reservations_xml: str,
    course_config_dates: dict[tuple[str, str], set[str]] | None = None,
    course_config_limits: dict[tuple[str, str, str], int] | None = None
) -> str:
    root = ET.fromstring(reservations_xml)

    for reservation in root.findall("reservation"):
        major = reservation.find("major")
        if major is None or not major.get("code"):
            raise ValueError("Reservation is missing required major code.")

        subject = reservation.get("subject")
        course_nbr = reservation.get("courseNbr")
        available_dates = None
        if course_config_dates and subject and course_nbr:
            available_dates = course_config_dates.get((subject, course_nbr))

        config_name = reservation_config_name(major.get("code"), available_dates)
        configuration = reservation.find("configuration")
        if configuration is None:
            configuration = ET.Element("configuration")
            reservation.insert(0, configuration)
        configuration.set("name", config_name)

        if course_config_limits and subject and course_nbr:
            config_limit = course_config_limits.get((subject, course_nbr, config_name))
            if config_limit is not None:
                reservation.set("limit", str(config_limit))

    ET.indent(root, space="  ")
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<!DOCTYPE reservations PUBLIC "-//UniTime//DTD University Course Timetabling/EN" "http://www.unitime.org/interface/Reservations.dtd">\n'
        f'{ET.tostring(root, encoding="unicode")}'
    )

def course_config_dates_from_offerings(offerings_xml: str) -> dict[tuple[str, str], set[str]]:
    root = ET.fromstring(offerings_xml)
    config_dates = defaultdict(set)

    for offering in root.findall("offering"):
        course = offering.find("course")
        if course is None:
            continue

        subject = course.get("subject")
        course_nbr = course.get("courseNbr")
        if not subject or not course_nbr:
            continue

        for config in offering.findall("config"):
            name = config.get("name", "")
            match = re.match(r"Config\s+(\d{2}-\d{2}-\d{2})$", name)
            if match:
                config_dates[(subject, course_nbr)].add(match.group(1))

    return dict(config_dates)

def course_config_limits_from_offerings(offerings_xml: str) -> dict[tuple[str, str, str], int]:
    root = ET.fromstring(offerings_xml)
    config_limits = {}

    for offering in root.findall("offering"):
        course = offering.find("course")
        if course is None:
            continue

        subject = course.get("subject")
        course_nbr = course.get("courseNbr")
        if not subject or not course_nbr:
            continue

        for config in offering.findall("config"):
            config_name = config.get("name")
            if not config_name:
                continue
            try:
                config_limits[(subject, course_nbr, config_name)] = int(config.get("limit", "0") or 0)
            except Exception:
                config_limits[(subject, course_nbr, config_name)] = 0

    return config_limits

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

def build_time_pattern_xml(name, start_times_hhmm=None, nbr_meetings=1, mins_per_meeting=None):
    day_codes = ["M", "T", "W", "Th", "F"]
    days_xml = "".join([f'<days code="{d}"/>' for d in day_codes])

    # Always dynamically parse durations from the name attribute
    mins_per_meeting = parse_minutes_from_name(name)

    # Ensure nbrSlotsPerMeeting is calculated as total_minutes / 5
    nbr_slots_per_meeting = int(mins_per_meeting // 5)

    # Dynamically calculate start times based on 15-minute sliding interval
    calculated_start_times = []
    current_time = 8 * 60  # 08:00 in minutes
    max_start = 18 * 60 - mins_per_meeting  # 18:00 minus duration
    
    while current_time <= max_start:
        if 9 * 60 + 1 <= current_time <= 9 * 60 + 59:
            current_time = 10 * 60  # Skip to 10:00
            continue
            
        hours = current_time // 60
        mins = current_time % 60
        calculated_start_times.append(f"{hours:02d}{mins:02d}")
        
        current_time += 15

    """Returns a single time pattern block."""
    times_xml = "".join(
        f'<time start="{t}"/>' for t in calculated_start_times
    )
    return f"""
    <timePattern name="{xml_escape(name)}" 
                 nbrMeetings="{nbr_meetings}" 
                 minsPerMeeting="{mins_per_meeting}" 
                 nbrSlotsPerMeeting="{nbr_slots_per_meeting}"
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

def map_min_per_week_to_pattern_name(min_per_week: int) -> str:
    """
    Maps minPerWeek value (in minutes) to UniTime Time Pattern name.

    Mapping:
    - 60 → "Auto 1 H"
    - 75 → "Auto 1 H 15 M"
    - 90 → "Auto 1 H 30 M"
    - 105 → "Auto 1 H 45 M"
    - 120 → "Auto 2 H"
    - 135 → "Auto 2 H 15 M"
    - 150 → "Auto 2 H 30 M"
    - 180 → "Auto 3 H"
    """
    mapping = {
        60: "Auto 1 H",
        75: "Auto 1 H 15 M",
        90: "Auto 1 H 30 M",
        105: "Auto 1 H 45 M",
        120: "Auto 2 H",
        135: "Auto 2 H 15 M",
        150: "Auto 2 H 30 M",
        180: "Auto 3 H"
    }
    return mapping.get(min_per_week, "Auto 2 H")

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

def build_reservations_xml(flat_records, course_config_dates=None):
    year, term = EXPECTED_ACADEMIC_SESSION.split()
    campus = year
    valid_subject_areas = load_valid_subject_areas()
    courses = {}

    for r in flat_records:
        course_number = r.get("course_number")
        if not course_number:
            continue

        # Parse subject_area from class_code to match offerings logic
        parsed_subject_area = subject_area_from_class_code(r.get("class_code"))
        if not parsed_subject_area:
            continue

        canonical_subject_area = valid_subject_areas.get(parsed_subject_area.upper())
        if not canonical_subject_area:
            continue

        key = (canonical_subject_area, course_number)
        course = courses.setdefault(
            key,
            {
                "subject_area": canonical_subject_area,
                "course_number": course_number,
                "intakes": {},
                "total_limit": 0,
            }
        )

        # Calculate total limit based on lecture classes only (matching offerings logic)
        instr_type = instructional_type_from_class_code(r.get("class_code"))
        if instr_type == "Lec":  # Only count lecture classes for total limit
            try:
                course["total_limit"] += int(r.get("total_students", 0))
            except Exception:
                pass

        # Collect unique intakes for this course
        for intake in r.get("intakes") or []:
            intake_code = str(intake.get("code") or "").strip()
            if intake_code:
                try:
                    students = int(intake.get("students", 0) or 0)
                except Exception:
                    students = 0
                previous_students = course["intakes"].get(intake_code)
                if previous_students is None or students > previous_students:
                    course["intakes"][intake_code] = students

    reservation_blocks = []
    for subject_area, course_number in sorted(courses):
        course = courses[(subject_area, course_number)]

        available_dates = None
        if course_config_dates:
            available_dates = course_config_dates.get((subject_area, course_number))

        for intake_code, students in sorted(course["intakes"].items()):
            academic_area = get_academic_area(intake_code)
            config_name = reservation_config_name(intake_code, available_dates)
            reservation_blocks.append(
                f'<reservation type="curriculum" subject="{xml_escape(subject_area)}" '
                f'courseNbr="{xml_escape(course_number)}" limit="{students}">'
                f'<configuration name="{xml_escape(config_name)}"/>'
                f'<academicArea abbreviation="{xml_escape(academic_area)}"/>'
                f'<academicClassification code="{xml_escape(RESERVATION_CLASSIFICATION)}"/>'
                f'<major code="{xml_escape(intake_code)}"/>'
                f'</reservation>'
            )

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE reservations PUBLIC "-//UniTime//DTD University Course Timetabling/EN" "http://www.unitime.org/interface/Reservations.dtd">
<reservations campus="{xml_escape(campus)}" term="{xml_escape(term)}" year="{xml_escape(year)}" incremental="true">
{''.join(reservation_blocks)}
</reservations>"""

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
            for r in valid_classes:
                instr_type = instructional_type_from_class_code(r.get("class_code"))
                subparts_dict[instr_type].append(r)

            lecture_classes = subparts_dict.get("Lec", [])
            tutorial_classes = subparts_dict.get("T", [])

            # Calculate total limit based on controlling classes (Lectures) to avoid double counting
            total_limit = 0
            for r in lecture_classes:
                try:
                    total_limit += int(r.get("total_students", 0))
                except Exception:
                    pass
            
            if total_limit == 0 and tutorial_classes:
                for r in tutorial_classes:
                    try:
                        total_limit += int(r.get("total_students", 0))
                    except Exception:
                        pass
            
            # Calculate minPerWeek for each type
            lec_min_per_week = 120
            if lecture_classes:
                time_pattern_name = lecture_classes[0].get("time_pattern_name", "")
                lec_min_per_week = parse_minutes_from_name(time_pattern_name)
            
            tut_min_per_week = 120
            if tutorial_classes:
                time_pattern_name = tutorial_classes[0].get("time_pattern_name", "")
                tut_min_per_week = parse_minutes_from_name(time_pattern_name)
            
            # Build subparts tree
            subparts_xml = ""
            if lecture_classes:
                lec_time_pattern_name = map_min_per_week_to_pattern_name(lec_min_per_week)
                subparts_xml += f'<subpart type="Lec" timePattern="{lec_time_pattern_name}" minPerWeek="{lec_min_per_week}" />\n'
            if tutorial_classes:
                tut_time_pattern_name = map_min_per_week_to_pattern_name(tut_min_per_week)
                subparts_xml += f'<subpart type="T" timePattern="{tut_time_pattern_name}" minPerWeek="{tut_min_per_week}"/>\n'

            # Build classes tree
            classes_xml = ""
            if lecture_classes:
                for r in lecture_classes:
                    instructor_xml = ""
                    class_id = shortened_class_id(r["class_code"])
                    lecturer_code = str(r.get("lecturer_code") or "").strip()
                    if lecturer_code and lecturer_code.upper() != "TBA":
                        instructor_xml = f'<instructor id="{xml_escape(lecturer_code)}" share="100" lead="true"/>'
                    suffix = class_suffix(r)
                    
                    lec_limit = 0
                    try:
                        lec_limit = int(r.get("total_students", 0))
                    except Exception:
                        pass
                    if lec_limit == 0:
                        lec_limit = total_limit if total_limit > 0 else 30
                    
                    classes_xml += f'  <class id="{xml_escape(class_id)}" type="Lec" suffix="{xml_escape(suffix)}" limit="{lec_limit}">\n'
                    if instructor_xml:
                        classes_xml += f'    {instructor_xml}\n'
                    classes_xml += '  </class>\n'
                    
            if tutorial_classes:
                for r in tutorial_classes:
                    tut_instructor_xml = ""
                    tut_class_id = shortened_class_id(r["class_code"])
                    tut_lecturer_code = str(r.get("lecturer_code") or "").strip()
                    if tut_lecturer_code and tut_lecturer_code.upper() != "TBA":
                        tut_instructor_xml = f'<instructor id="{xml_escape(tut_lecturer_code)}" share="100" lead="true"/>'
                    suffix = class_suffix(r)
                    
                    tut_limit = 0
                    try:
                        tut_limit = int(r.get("total_students", 0))
                    except Exception:
                        pass
                    if tut_limit == 0:
                        tut_limit = total_limit if total_limit > 0 else 30
                    
                    classes_xml += f'  <class id="{xml_escape(tut_class_id)}" type="T" suffix="{xml_escape(suffix)}" limit="{tut_limit}">\n'
                    if tut_instructor_xml:
                        classes_xml += f'    {tut_instructor_xml}\n'
                    classes_xml += '  </class>\n'

            off_action = "insert"
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
{OFFERINGS_DOCTYPE}
<offerings term="{term}" year="{year}" campus="{campus}" incremental="true">
{offerings_body}
</offerings>"""

    offerings_xml = split_offering_configs_by_class_date(offerings_xml)
    validate_offerings_xml(offerings_xml)

    course_config_dates = course_config_dates_from_offerings(offerings_xml)
    reservations_xml = build_reservations_xml(flat_records, course_config_dates)
    reservations_xml = update_reservation_configurations(reservations_xml, course_config_dates)

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
        reservations_xml,
    )

    return {
        "zip_path": zip_path,
        "sections": {
            "session": session_xml,
            "time_patterns": time_patterns_xml,
            "staff": staff_xml,
            "curricula": curricula_xml,
            "offerings": offerings_xml,
            "reservations": reservations_xml,
        },
    }

def create_unitime_zip_package(output_zip_path, session_xml, time_patterns_xml, staff_xml, curricula_xml, offerings_xml, reservations_xml):
    """
    Creates a zip archive containing the four required UniTime XML files.
    """
    try:
        with zipfile.ZipFile(output_zip_path, 'w', zipfile.ZIP_DEFLATED) as unitime_zip:
            # Writing each individual XML string into its own file inside the zip
            unitime_zip.writestr("01_sessions.xml", session_xml)
            unitime_zip.writestr("02_time_patterns.xml", time_patterns_xml)
            unitime_zip.writestr("03_instructors.xml", staff_xml)
            unitime_zip.writestr("04_offerings.xml", offerings_xml)
            unitime_zip.writestr("05_curricula.xml", curricula_xml)
            unitime_zip.writestr("06_reservations.xml", reservations_xml)

            
        print(f"Successfully created: {output_zip_path}")
        return output_zip_path
    except Exception as e:
      print(f"Error creating zip: {e}")
      return None
