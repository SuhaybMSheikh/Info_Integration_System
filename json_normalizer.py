import re

def parse_intakes(raw: str):
    if not raw:
        return []

    intakes = []

    parts = raw.split(",")

    for p in parts:
        p = p.strip()

        # Find last (...) group containing digits
        match = re.search(r"\((\d+)\)\s*$", p)
        if not match:
            continue

        students = int(match.group(1))

        # Remove final (number) part to get intake code
        code = re.sub(r"\(\d+\)\s*$", "", p).strip()

        intakes.append({
            "code": code,
            "students": students
        })

    return intakes

def normalize_records(records):
    for r in records:
        r["subject_area"] = r["faculty"]
        r["course_number"] = parse_course_number(r["subject_raw"])
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

def parse_course_number(subject_full_code: str) -> str:
    parts = subject_full_code.split("-")

    # Remove last two parts (L-1 or T-1 or P-1)
    if len(parts) >= 2:
        return "-".join(parts[:-2])

    return subject_full_code