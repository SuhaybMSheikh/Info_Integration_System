def validate_records(records):

    # seen = set()

    for r in records:

        # if r["class_code"] in seen:
        #     raise ValueError(f"Duplicate class code: {r['class_code']}")
        #
        # seen.add(r["class_code"])

        if r["duration_weeks"] <= 0:
            raise ValueError(
                f"Invalid duration weeks for {r['class_code']}"
            )

        if r["duration_minutes"] <= 0:
            raise ValueError(
                f"Invalid duration minutes for {r['class_code']}"
            )