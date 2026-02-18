def validate_no_duplicate_class_codes(records):
    seen = set()
    for r in records:
        code = r["class_code"]
        if code in seen:
            raise ValueError(f"Duplicate class_code detected: {code}")
        seen.add(code)


def validate_no_duplicate_curricula(records):
    seen = set()
    for r in records:
        for intake in r.get("intakes", []):
            code = intake["code"]
            if code in seen:
                continue  # multiple projections allowed
            seen.add(code)


def validate_student_totals(records):
    for r in records:
        intakes = r.get("intakes", [])
        if not intakes:
            continue

        intake_sum = sum(i["students"] for i in intakes)
        total_students = r["total_students"]

        if intake_sum != total_students:
            raise ValueError(
                f"Student mismatch in {r['class_code']} "
                f"(intakes total={intake_sum}, class total={total_students})"
            )


def validate_required_fields(records):
    required = [
        "subject_area",
        "course_number",
        "class_code",
        "instructional_type",
        "lecturer_code",
        "total_students",
        "time_pattern_name",
    ]

    for r in records:
        for field in required:
            if field not in r or r[field] in (None, "", []):
                raise ValueError(
                    f"Missing required field '{field}' in record: {r.get('class_code')}"
                )


def run_all_pre_import_validations(records):
    validate_required_fields(records)
    validate_no_duplicate_class_codes(records)
    validate_no_duplicate_curricula(records)
    # validate_student_totals(records)