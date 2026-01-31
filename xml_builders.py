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
def build_data_exchange_xml(records, time_patterns):
    instructors = {}
    offerings = {}
    time_pattern_xml_blocks = []

    # Time Patterns
    for tp_name, starts in time_patterns.items():
        time_pattern_xml_blocks.append(
            build_time_pattern_xml(tp_name, starts)
        )

    # Records
    for r in records:
        # Instructors
        instructors[r["lecturer_code"]] = f"""
<instructor>
  <externalId>{xml_escape(r["lecturer_code"])}</externalId>
  <name>{xml_escape(r["lecturer_name"])}</name>
</instructor>
"""

        # Classes
        class_xml = f"""
<class>
  <externalId>{xml_escape(r["class_code"])}</externalId>
  <instructionalType>{xml_escape(r["instructional_type"])}</instructionalType>
  <limit>{r["total_students"]}</limit>
  <weeks>{r["duration_weeks"]}</weeks>
  <timePattern>{xml_escape(r["time_pattern_name"])}</timePattern>
</class>
"""

        key = (r["subject_area"], r["course_number"])
        offerings.setdefault(key, []).append(class_xml)

    #  Assemble XML
    instructors_xml = "".join(instructors.values())

    offerings_xml = ""
    for (sa, cn), classes in offerings.items():
        offerings_xml += f"""
<instructionalOffering>
  <subject>{xml_escape(sa)}</subject>
  <courseNumber>{xml_escape(cn)}</courseNumber>
  <classes>
    {''.join(classes)}
  </classes>
</instructionalOffering>
"""

    session_xml = build_session_xml()
    curricula_xml = build_curricula_xml(records)

    #  Final XML
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