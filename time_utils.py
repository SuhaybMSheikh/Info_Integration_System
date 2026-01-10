# time_utils.py

import re
from math import ceil

ROUND_TO_MINUTES = 15

def parse_duration_to_minutes(text: str) -> int:
    """
    Examples:
    1H 30M -> 90
    48M -> 48
    2H 48M -> 168
    """
    hours = 0
    minutes = 0

    h_match = re.search(r"(\d+)\s*H", text.upper())
    m_match = re.search(r"(\d+)\s*M", text.upper())

    if h_match:
        hours = int(h_match.group(1))
    if m_match:
        minutes = int(m_match.group(1))

    return hours * 60 + minutes


def round_duration(minutes: int) -> int:
    """
    Rounds UP to nearest 15 minutes.
    """
    return int(ceil(minutes / ROUND_TO_MINUTES) * ROUND_TO_MINUTES)


def normalize_duration(text: str) -> int:
    raw = parse_duration_to_minutes(text)
    return round_duration(raw)