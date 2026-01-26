from datetime import datetime

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

    #  Final XML
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<dataExchange>

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