from xml_builders import build_data_exchange_xml

def records_to_xml(grouped_records, flat_records, time_patterns, existing_courses, existing_classes):
    return build_data_exchange_xml(
        grouped_records,
        flat_records,
        time_patterns,
        existing_courses,
        existing_classes
    )