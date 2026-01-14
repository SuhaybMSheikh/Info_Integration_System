def validate_records(records):
    seen = set()
    for r in records:
        if r["class_code"] in seen:
            raise ValueError("Duplicate class code")
        seen.add(r["class_code"])

        if r["total_students"] <= 0:
            raise ValueError("Invalid student count")