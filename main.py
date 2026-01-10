from excel_loader import load_excel
from time_utils import parse_duration_to_minutes, coerce_duration
from time_patterns import time_pattern_name
from xml_builders import (
    build_instructional_offerings_xml,
    build_time_pattern_xml
)
from unitime_client import post_xml
from time_patterns import generate_start_times

def main():
    records = load_excel("input.xlsx")

    time_patterns_to_create = {}

    for r in records:
        raw_minutes = parse_duration_to_minutes(r["class_duration_raw"])
        coerced_minutes = coerce_duration(raw_minutes)

        r["duration_minutes"] = coerced_minutes
        r["time_pattern_name"] = time_pattern_name(coerced_minutes)

        time_patterns_to_create[coerced_minutes] = r["time_pattern_name"]

    # Build XML
    xml_parts = []

    for minutes in time_patterns_to_create:
        xml_parts.append(
            build_time_pattern_xml(
                minutes,
                start_times=generate_start_times(minutes)
            )
        )

    xml_parts.append(
        build_instructional_offerings_xml(records)
    )

    post_xml("\n".join(xml_parts))

if __name__ == "__main__":
    main()