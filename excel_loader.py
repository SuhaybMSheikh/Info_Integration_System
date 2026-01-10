import pandas as pd

def load_excel(path: str) -> list[dict]:
    df = pd.read_excel(path)
    df.columns = [c.strip() for c in df.columns]

    rows = []
    for _, row in df.iterrows():
        rows.append({
            "week_beginning": row["Week Beginning"],
            "intakes": [i.strip() for i in row["Intakes"].split(",")],
            "subject": row["Subjects"].strip(),
            "lecturer_name": row["Lecturer Name"].strip(),
            "lecturer_code": row["Lecturer Code"].strip(),
            "class_duration_raw": row["Class Duration"].strip(),
            "faculty": row["Faculty"].strip(),
            "duration_weeks": int(row["Duration"]),
            "total_students": int(row["Total Students"]),
            "class_code": row["Class Code"].strip()
        })

    return rows