def validate_json(data: dict):
    if "modules" not in data:
        raise ValueError("No modules found")

    for module in data["modules"]:
        if "courseCode" not in module:
            raise ValueError("Module missing courseCode")

        for io in module["instructionalOfferings"]:
            cls = io["class"]

            if cls["expectedStudents"] <= 0:
                raise ValueError("Invalid expectedStudents")

            if cls["durationMinutes"] <= 0:
                raise ValueError("Invalid durationMinutes")