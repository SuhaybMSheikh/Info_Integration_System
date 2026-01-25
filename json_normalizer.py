def normalize_records(records):
    for r in records:
        r["subject_area"] = r["faculty"]
        r["course_number"] = r["subject_raw"]
    return records