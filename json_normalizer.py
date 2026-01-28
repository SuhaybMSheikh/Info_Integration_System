def normalize_records(records):
    for r in records:
        r["subject_area"] = r["faculty"]
        r["course_number"] = r["subject_raw"]
        r["instructional_type"] = parse_instructional_type(r["subject_raw"])
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
