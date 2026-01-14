from excel_loader import load_excel
from json_normalizer import normalize_records
from json_validators import validate_records
from time_utils import parse_duration_to_minutes, coerce_duration
from time_patterns import time_pattern_name, generate_start_times
from xml_builders import build_time_pattern_xml
from unitime_client import post_xml, get_sessions
from unitime_checks import validate_academic_session
from config import DEFAULT_BREAK_MINUTES, DRY_RUN

def main():
    records = load_excel("input.xlsx")
    records = normalize_records(records)
    validate_records(records)

    validate_academic_session(get_sessions())

    time_patterns = {}
    for r in records:
        mins = coerce_duration(parse_duration_to_minutes(r["class_duration_raw"]))
        r["duration_minutes"] = mins
        r["time_pattern_name"] = time_pattern_name(mins)
        time_patterns[mins] = r["time_pattern_name"]

    xml = ""
    for mins, name in time_patterns.items():
        xml += build_time_pattern_xml(
            name, mins, DEFAULT_BREAK_MINUTES, generate_start_times()
        )

    from json_to_xml_mapper import records_to_xml
    xml += records_to_xml(records)

    if DRY_RUN:
        print(xml)
    else:
        post_xml(xml)

if __name__ == "__main__":
    main()