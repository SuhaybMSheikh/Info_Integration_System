UNITIME_BASE_URL = "https://unitime3.apu.edu.my/UniTime"
DATA_EXCHANGE_ENDPOINT = f"{UNITIME_BASE_URL}/dataExchange"

USERNAME = "admin"
PASSWORD = "admin"

ACADEMIC_SESSION = "2025-2026"
DEPARTMENT_CODE = "APP"

# Time patterns must already exist in UniTime
TIME_PATTERNS = {
    90: "90"
}

# Control behavior
ALLOW_DATE_PATTERN_CREATION = True
FAIL_ON_MISSING_CURRICULUM = True