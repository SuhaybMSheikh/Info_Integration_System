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