from xml_builders import build_data_exchange_xml, build_data_exchange_zip

def records_to_xml(grouped_records, flat_records, time_patterns, existing_courses, existing_classes):
    return build_data_exchange_zip(
        grouped_records,
        flat_records,
        time_patterns,
        existing_courses,
        existing_classes
    )