UNITIME_BASE_URL = "https://unitime3.apu.edu.my/UniTime"
DATA_EXCHANGE_ENDPOINT = f"{UNITIME_BASE_URL}/dataExchange"

USERNAME = "unitime_integration"
PASSWORD = "password"

EXPECTED_ACADEMIC_SESSION = "2026 2026"

# Operational hours (used later by time pattern logic)
DAY_START = "08:30"
DAY_END = "17:00"
TIME_STEP_MINUTES = 15
DEFAULT_BREAK_MINUTES = 15

# Control behavior
ALLOW_DATE_PATTERN_CREATION = True
FAIL_ON_MISSING_CURRICULUM = True
DRY_RUN = True