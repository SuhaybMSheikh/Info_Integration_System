UNITIME_BASE_URL = "https://unitime3.apu.edu.my/UniTime"
DATA_EXCHANGE_ENDPOINT = f"{UNITIME_BASE_URL}/dataExchange"

USERNAME = "unitime_integration"
PASSWORD = "password"

ACADEMIC_SESSION = "2025 2025"

# Operational hours (used later by time pattern logic)
DAY_START = "08:30"
DAY_END = "17:00"
TIME_STEP_MINUTES = 15

# Control behavior
ALLOW_DATE_PATTERN_CREATION = True
FAIL_ON_MISSING_CURRICULUM = True