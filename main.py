import sys
from datetime import datetime
# from excel_loader import load_excel
from json_loader import fetch_api_payload, flatten_api_payload
from json_normalizer import normalize_records, group_records
from json_validators import validate_records
from time_utils import parse_duration_to_minutes, coerce_duration
from time_patterns import time_pattern_name, generate_start_times
from xml_builders import build_time_pattern_xml

# === UniTime dependencies (DISABLED FOR OFFLINE MODE) ===
# from unitime_client import post_xml, get_sessions
# from unitime_checks import validate_academic_session, detect_instructor_conflicts
# from unitime_time_patterns import get_existing_time_patterns
# from time_pattern_resolver import resolve_time_pattern
# from unitime_courses import get_existing_courses
# from unitime_classes import get_existing_classes

from config import DEFAULT_BREAK_MINUTES, DRY_RUN
from pre_import_validators import run_all_pre_import_validations
from time_pattern_validators import validate_time_pattern_spacing


def main():
    # === UniTime session validation (DISABLED) ===
    # print("Fetching sessions from UniTime...")
    # sessions = get_sessions()
    #
    # print("Validating academic session...")
    # validate_academic_session(sessions)

    print("Fetching data from IIS API...")

    payload = fetch_api_payload()
    flattened = flatten_api_payload(payload)

    records = normalize_records(flattened)

    validate_records(records)

    grouped_records = group_records(records)

    # === UniTime existing data checks (DISABLED) ===
    # existing_courses = get_existing_courses()
    # existing_patterns = get_existing_time_patterns()
    # existing_classes = get_existing_classes()

    existing_courses = {}
    existing_patterns = {}
    existing_classes = {}

    time_patterns = {}

    for r in records:
        mins = coerce_duration(parse_duration_to_minutes(r["class_duration_raw"]))

        r["duration_minutes"] = mins
        r["time_pattern_name"] = time_pattern_name(mins)

        time_patterns[mins] = r["time_pattern_name"]

    print("\n=== PRE-FLIGHT VALIDATION ===")

    try:

        run_all_pre_import_validations(records)
        print("Record validation passed.")

        # Instructor conflict validation using UniTime data
        # === (DISABLED — still possible locally if needed) ===
        # detect_instructor_conflicts(grouped_records)

        print("Instructor conflict validation skipped (offline mode).")

        print("All validations passed successfully.")

    except Exception as e:

        print("\n VALIDATION FAILED")
        print(str(e))
        sys.exit(1)

    xml = ""

    time_pattern_starts = {}

    for mins, name in time_patterns.items():

        starts = generate_start_times(mins)

        validate_time_pattern_spacing(
            duration_minutes=mins,
            break_minutes=DEFAULT_BREAK_MINUTES,
            start_times=starts
        )

        time_pattern_starts[name] = starts

    # === UniTime time pattern existence checks (DISABLED) ===
    for name, starts in time_pattern_starts.items():

        # if resolve_time_pattern(name, existing_patterns):
        #     print(f"Time pattern already exists: {name}")
        # else:
        #     print(f"Creating time pattern: {name}")
        #     xml += build_time_pattern_xml(name, starts)

        print(f"Generating time pattern: {name}")
        xml += build_time_pattern_xml(name, starts)

    from json_to_xml_mapper import records_to_xml

    xml = records_to_xml(
        grouped_records,
        time_pattern_starts,
        existing_courses,
        existing_classes
    )

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    snapshot_filename = f"xml_snapshot_{timestamp}.xml"

    with open(snapshot_filename, "w", encoding="utf-8") as f:
        f.write(xml)

    print(f"XML snapshot saved to: {snapshot_filename}")

    # === XML Export (Manual Import Mode) ===

    if not DRY_RUN:

        with open("unitime_export.xml", "w", encoding="utf-8") as f:
            f.write(xml)

        print("XML file generated: unitime_export.xml")

    else:
        print("Dry run enabled — XML not generated.")

    # === UniTime API Push (DISABLED) ===

    # if not DRY_RUN:
    #
    #     confirm = input(
    #         "\n You are about to push data to UniTime.\n"
    #         "Type 'CONFIRM' to proceed: "
    #     )
    #
    #     if confirm != "CONFIRM":
    #         print("Push aborted.")
    #         sys.exit(0)
    #
    #     try:
    #         post_xml(xml)
    #     except Exception as e:
    #         print("\n IMPORT FAILED")
    #         print(str(e))
    #         sys.exit(1)
    #
    # else:
    #     print("Dry run enabled — XML not sent.")


if __name__ == "__main__":
    main()