def time_pattern_name(duration_minutes: int) -> str:
    hours = duration_minutes // 60
    minutes = duration_minutes % 60

    parts = []
    if hours:
        parts.append(f"{hours} H")
    if minutes:
        parts.append(f"{minutes} M")

    return f"Auto {' '.join(parts)}"

def generate_start_times(start=830, end=1700, step=15) -> list[int]:
    return list(range(start, end + 1, step))