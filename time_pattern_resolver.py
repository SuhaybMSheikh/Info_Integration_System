def resolve_time_pattern(name: str, existing_patterns: set[str]) -> bool:
    """
    available_patterns example:
    {
        60: pattern_id,
        90: pattern_id,
        120: pattern_id,
        180: pattern_id
    }
    """
    return name in existing_patterns