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

def build_class_xml(classes: list) -> str:
    xml = ["<classes>"]

    for cls in classes:
        xml.append(f"""
        <class externalId="{cls['external_id']}">
            <course>{cls['course_nbr']}</course>
            <expectedCapacity>{cls['capacity']}</expectedCapacity>
            <maxExpectedCapacity>{cls['capacity']}</maxExpectedCapacity>
            <instructor>{cls['instructor']}</instructor>
            <timePattern>{cls['time_pattern']}</timePattern>
            <datePattern>{cls['date_pattern']}</datePattern>
        </class>
        """)

    xml.append("</classes>")
    return "\n".join(xml)