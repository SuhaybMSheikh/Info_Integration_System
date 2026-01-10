def resolve_time_pattern(duration_minutes: int, available_patterns: dict) -> int:
    """
    available_patterns example:
    {
        60: pattern_id,
        90: pattern_id,
        120: pattern_id,
        180: pattern_id
    }
    """
    if duration_minutes not in available_patterns:
        raise RuntimeError(
            f"No UniTime time pattern for duration {duration_minutes} minutes"
        )

    return available_patterns[duration_minutes]