def time_pattern_name(duration_minutes: int) -> str:
    hours = duration_minutes // 60
    minutes = duration_minutes % 60

    parts = []
    if hours:
        parts.append(f"{hours} H")
    if minutes:
        parts.append(f"{minutes} M")

    label = " ".join(parts)
    return f"Updated {label} break 15"

def generate_start_times(duration_minutes: int) -> list[int]:
    start = 830
    end = 1700
    step = 15

    return list(range(start, end + 1, step))