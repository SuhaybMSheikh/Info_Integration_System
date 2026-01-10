def build_instructor_xml(instructors: dict) -> str:
    xml = ["<instructors>"]

    for code, name in instructors.items():
        xml.append(f"""
        <instructor externalId="{code}">
            <name>{name}</name>
            <department>APP</department>
        </instructor>
        """)

    xml.append("</instructors>")
    return "\n".join(xml)

def build_course_xml(courses: set) -> str:
    xml = ["<courseOfferings>"]

    for subject, course_nbr in courses:
        xml.append(f"""
        <courseOffering subject="{subject}" courseNbr="{course_nbr}">
            <title>{course_nbr}</title>
            <department>APP</department>
        </courseOffering>
        """)

    xml.append("</courseOfferings>")
    return "\n".join(xml)

def build_class_xml(record):
    return f"""
    <class>
        <externalId>{record['class_code']}</externalId>
        <limit>{record['total_students']}</limit>
        <timePattern>{record['time_pattern_name']}</timePattern>
    </class>
    """

def build_time_pattern_xml(duration_minutes: int, start_times: list[str]) -> str:
    times_xml = "".join(
        f"<time start=\"{t}\" />" for t in start_times
    )

    return f"""
    <timePattern>
        <name>{duration_minutes}</name>
        <minutes>{duration_minutes}</minutes>
        <breakTime>15</breakTime>
        <times>
            {times_xml}
        </times>
    </timePattern>
    """