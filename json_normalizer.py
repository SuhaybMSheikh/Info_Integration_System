def normalize_records(records):
    for r in records:
        r["subject_area"] = r["faculty"]
        r["course_number"] = r["subject_raw"].split("-")[0]
    return records