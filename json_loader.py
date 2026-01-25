import json

def load_json(path: str) -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def flatten_api_payload(payload):
    records = []

    for block in payload:
        week_begins = block["week_begins"]

        for subj in block["subjects"]:
            area = subj["subject"]["area"]
            full_code = subj["subject"]["code"]

            for cls in subj["classes"]:
                records.append({
                    "week_begins": week_begins,
                    "faculty": area,
                    "subject_raw": full_code,
                    "class_code": cls["code"],
                    "class_duration_raw": cls["duration"],
                    "duration_weeks": cls["weeks"],
                    "total_students": cls["number_of_students"],
                    "lecturer_code": cls["lecturer"]["code"] or "TBA",
                    "lecturer_name": cls["lecturer"]["username"] or "TBA",
                    "intakes": cls["intakes"]
                })

    return records
