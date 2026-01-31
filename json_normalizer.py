import re

def parse_intakes(raw: str):
    if not raw:
        return []

    intakes = []
    parts = raw.split(",")

    for p in parts:
        match = re.search(r"([A-Z0-9]+)\s*\((\d+)\)", p.strip())
        if match:
            intakes.append({
                "code": match.group(1),
                "students": int(match.group(2))
            })

    return intakes

def normalize_records(records):
    for r in records:
        r["subject_area"] = r["faculty"]
        r["course_number"] = r["subject_raw"]
        r["instructional_type"] = parse_instructional_type(r["subject_raw"])
        r["intakes"] = parse_intakes(r.get("intakes_raw"))
    return records

def parse_instructional_type(subject_full_code: str) -> str:
    code = subject_full_code.upper()

    if "-L-" in code:
        return "Lecture"
    if "-T-" in code:
        return "Tutorial"
    if "-P-" in code:
        return "Practical"

    # Safe default
    return "Lecture"
