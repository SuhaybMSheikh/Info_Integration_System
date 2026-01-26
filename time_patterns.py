def time_pattern_name(duration_minutes: int) -> str:
    hours = duration_minutes // 60
    minutes = duration_minutes % 60

    parts = []
    if hours:
        parts.append(f"{hours} H")
    if minutes:
        parts.append(f"{minutes} M")

    return f"Auto {' '.join(parts)}"

def generate_start_times(duration_minutes: int,
                         day_start=8*60,
                         day_end=18*60):
    starts = []
    current = day_start

    while current + duration_minutes <= day_end:
        hh = current // 60
        mm = current % 60
        starts.append(f"{hh:02d}{mm:02d}")
        current += duration_minutes

    return starts