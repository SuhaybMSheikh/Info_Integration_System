import pandas as pd

def load_excel(path: str) -> list[dict]:
    df = pd.read_excel(path)
    df.columns = [c.strip() for c in df.columns]

    records = []
    for _, row in df.iterrows():
        records.append({
            "week_begins": row["Week Begins"],
            "intakes_raw": row["Intakes"],
            "subject_raw": row["Subjects"],
            "lecturer_name": row["Lecturer Name"],
            "lecturer_code": row["Lecturer Code"],
            "class_duration_raw": row["Class Duration"],
            "faculty": row["Faculty"],
            "duration_weeks": int(row["Duration"]),
            "total_students": int(row["Total Students"]),
            "class_code": row["Class Code"],
        })

    return records