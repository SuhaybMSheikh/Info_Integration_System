from config import EXPECTED_ACADEMIC_SESSION

def validate_academic_session(sessions):
    expected_year, expected_term = EXPECTED_ACADEMIC_SESSION.split()

    for s in sessions:
        if (
            str(s.get("academicYear")) == expected_year and
            s.get("term") == expected_term and
            s.get("active")
        ):
            print("Academic session validated.")
            return s["id"]

    raise RuntimeError(
        f"Expected academic session '{EXPECTED_ACADEMIC_SESSION}' not active."
    )

def detect_instructor_conflicts(grouped_records, time_pattern_starts):

    instructor_windows = {}

    for group in grouped_records:
        for r in group["classes"]:

            instructor = r["lecturer_code"]
            duration = r["duration_minutes"]
            pattern_name = r["time_pattern_name"]

            starts = time_pattern_starts.get(pattern_name, [])

            for start_hhmm in starts:

                start = hhmm_to_minutes(start_hhmm)
                end = start + duration

                key = instructor

                if key not in instructor_windows:
                    instructor_windows[key] = []

                # Check overlap against existing windows
                for existing_start, existing_end in instructor_windows[key]:
                    if start < existing_end and existing_start < end:
                        raise RuntimeError(
                            f"Instructor conflict detected:\n"
                            f"Instructor: {instructor}\n"
                            f"New: {start_hhmm} -> {end}\n"
                            f"Conflicts with existing window."
                        )

                instructor_windows[key].append((start, end))

    print("Advanced instructor conflict validation passed.")

def validate_unique_class_ids(grouped_records):

    seen = set()

    for group in grouped_records:
        for r in group["classes"]:
            cid = r["class_code"]

            if cid in seen:
                raise Exception(f"Duplicate class externalId detected: {cid}")

            seen.add(cid)

def hhmm_to_minutes(hhmm: str) -> int:
    hours = int(hhmm[:2])
    minutes = int(hhmm[2:])
    return hours * 60 + minutes