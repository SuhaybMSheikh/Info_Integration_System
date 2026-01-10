from excel_loader import load_excel
from time_utils import normalize_duration
from time_patterns import TIME_PATTERN_MAP
from xml_builders import build_instructor_xml
from unitime_client import post_xml

def main():
    records = load_excel("input.xlsx")

    for r in records:
        duration_minutes = normalize_duration(r["class_duration_raw"])

        if duration_minutes not in TIME_PATTERN_MAP:
            raise RuntimeError(
                f"No time pattern for rounded duration {duration_minutes} minutes"
            )

        r["duration_minutes"] = duration_minutes
        r["time_pattern_name"] = TIME_PATTERN_MAP[duration_minutes]

    xml_payload = build_instructor_xml(records)
    post_xml(xml_payload)

if __name__ == "__main__":
    main()