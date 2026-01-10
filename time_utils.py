# time_utils.py

import re
from math import ceil

ROUND_TO_MINUTES = 15

def parse_duration_to_minutes(text: str) -> int:
    text = text.upper()

    hours = 0
    minutes = 0

    h = re.search(r"(\d+)\s*H", text)
    m = re.search(r"(\d+)\s*M", text)

    if h:
        hours = int(h.group(1))
    if m:
        minutes = int(m.group(1))

    return hours * 60 + minutes


def round_up_duration(minutes: int) -> int:
    return int(ceil(minutes / ROUND_TO_MINUTES) * ROUND_TO_MINUTES)


def normalize_duration(text: str) -> int:
    raw = parse_duration_to_minutes(text)
    return round_up_duration(raw)