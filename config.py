import os
from dotenv import load_dotenv
load_dotenv()

UNITIME_BASE_URL = "https://unitime3.apu.edu.my/UniTime"
DATA_EXCHANGE_ENDPOINT = f"{UNITIME_BASE_URL}/api/exchange"

API_BASE_URL = "https://610bt8b6g2.execute-api.ap-southeast-1.amazonaws.com/dev/iis-temp/unitime/schedules"

API_KEY = os.getenv("IIS_API_KEY")

API_START_DATE = "2026-01-01"
API_END_DATE = "2026-01-31"

USERNAME = os.getenv("USERNAME")
PASSWORD = os.getenv("PASSWORD")

EXPECTED_ACADEMIC_SESSION = "2026 2026"

# Operational hours
DAY_START = "08:30"
DAY_END = "17:00"
TIME_STEP_MINUTES = 15
DEFAULT_BREAK_MINUTES = 15

# Control behavior
ALLOW_DATE_PATTERN_CREATION = True
FAIL_ON_MISSING_CURRICULUM = True
DRY_RUN = True