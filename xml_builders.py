from datetime import datetime

def xml_escape(s: str) -> str:
    return (
        s.replace("&", "&amp;")
         .replace("<", "&lt;")
         .replace(">", "&gt;")
         .replace('"', "&quot;")
         .replace("'", "&apos;")
    )

def format_date(d: str) -> str:
    return datetime.strptime(d, "%d/%m/%Y").strftime("%Y-%m-%d")


def build_time_pattern_xml(name, minutes, break_time, start_times):
    times = "\n".join(f'<time start="{t}"/>' for t in start_times)
    return f"""
<timePattern>
  <name>{xml_escape(name)}</name>
  <minutes>{minutes}</minutes>
  <breakTime>{break_time}</breakTime>
  <times>{times}</times>
</timePattern>
"""


def build_instructor_xml(code, name):
    return f"""
<instructor>
  <externalId>{xml_escape(code)}</externalId>
  <firstName>{xml_escape(name)}</firstName>
  <lastName>{xml_escape(name)}</lastName>
</instructor>
"""


def build_class_xml(r):
    return f"""
<class>
  <externalId>{xml_escape(r['class_code'])}</externalId>
  <limit>{r['total_students']}</limit>
  <timePattern>{xml_escape(r['time_pattern_name'])}</timePattern>
  <instructor>{xml_escape(r['lecturer_code'])}</instructor>
</class>
"""


def build_instructional_offerings_xml(records):
    instructors = {}
    offerings = {}

    for r in records:
        instructors[r["lecturer_code"]] = r["lecturer_name"]
        key = (r["subject_area"], r["course_number"])
        offerings.setdefault(key, []).append(build_class_xml(r))

    instructors_xml = "".join(
        build_instructor_xml(c, n) for c, n in instructors.items()
    )

    offerings_xml = ""
    for (sa, cn), classes in offerings.items():
        offerings_xml += f"""
<instructionalOffering>
  <subject>{xml_escape(sa)}</subject>
  <courseNumber>{xml_escape(cn)}</courseNumber>
  <classes>{''.join(classes)}</classes>
</instructionalOffering>
"""

    return f"""<?xml version="1.0"?>
<dataExchange>
  <instructors>{instructors_xml}</instructors>
  <instructionalOfferings>{offerings_xml}</instructionalOfferings>
</dataExchange>
"""