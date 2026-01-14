import re
from math import ceil

ROUND_TO_MINUTES = 15

def parse_duration_to_minutes(text: str) -> int:
    text = text.upper()
    hours = minutes = 0

    h = re.search(r"(\d+)\s*H", text)
    m = re.search(r"(\d+)\s*M", text)

    if h:
        hours = int(h.group(1))
    if m:
        minutes = int(m.group(1))

    return hours * 60 + minutes


def coerce_duration(minutes: int) -> int:
    if minutes == 48:
        return 60

    if minutes == 168:   # 2H 48M
        return 180

    if minutes == 210:   # 3H 30M
        return 210

    # Default: round UP to nearest 15
    return ((minutes + 14) // 15) * 15