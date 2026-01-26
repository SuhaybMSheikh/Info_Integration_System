from xml_builders import build_data_exchange_xml

def records_to_xml(records, time_patterns):
    return build_data_exchange_xml(records, time_patterns)