from datetime import datetime, timedelta

DAY_END = 18 * 60  # 18:00 in minutes


def hhmm_to_minutes(hhmm: str) -> int:
    return int(hhmm[:2]) * 60 + int(hhmm[2:])


def validate_time_pattern_spacing(duration_minutes, break_minutes, start_times):
    """
    Ensures:
    - No overlap between consecutive start times
    - End time does not exceed 18:00
    """

    for i, start in enumerate(start_times):
        start_min = hhmm_to_minutes(start)
        end_min = start_min + duration_minutes

        # Check day boundary
        if end_min > DAY_END:
            raise ValueError(
                f"Time pattern invalid: class ending at {start} exceeds 18:00"
            )

        # Check overlap with next slot
        if i < len(start_times) - 1:
            next_start_min = hhmm_to_minutes(start_times[i + 1])

            required_gap = duration_minutes + break_minutes

            if next_start_min < start_min + required_gap:
                raise ValueError(
                    f"Time overlap detected between {start} and "
                    f"{start_times[i + 1]}"
                )