from config import EXPECTED_ACADEMIC_SESSION

def validate_academic_session(sessions):
    for s in sessions:
        if s.get("academicYear") == EXPECTED_ACADEMIC_SESSION and s.get("active"):
            return s["id"]
    raise RuntimeError("Expected academic session not active")