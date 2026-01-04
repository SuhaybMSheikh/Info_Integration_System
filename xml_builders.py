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