from excel_loader import load_excel
from json_normalizer import normalize_rows
from json_validators import validate_json
from json_to_xml_mapper import json_to_xml_payloads
from unitime_client import post_xml

def main():
    df = load_excel("input.xlsx")
    rows = df.to_dict(orient="records")

    canonical_json = normalize_rows(rows)
    validate_json(canonical_json)

    payloads = json_to_xml_payloads(canonical_json)

    post_xml(payloads["instructors"])
    post_xml(payloads["courses"])
    post_xml(payloads["classes"])

    print("Import completed successfully.")

if __name__ == "__main__":
    main()