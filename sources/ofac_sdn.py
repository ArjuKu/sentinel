import csv, io, re
from collections import defaultdict
from sources.base import http_get, normalise_record, with_fallback, opensanctions_csv
from config import OFAC_SDN_URL, OFAC_SDN_ALT_URL


SDN_COLUMNS = [
    "ent_num", "SDN_Name", "SDN_Type", "Program", "Title",
    "Call_Sign", "Vess_type", "Tonnage", "GRT", "Vess_flag",
    "Vess_owner", "Remarks"
]


def parse_sdn_csv(content: str) -> list[dict]:
    records = {}
    reader = csv.reader(io.StringIO(content))
    for row in reader:
        if not row or len(row) < 12:
            continue
        ent_num = row[0].strip()
        name = row[1].strip() if len(row) > 1 else ""
        sdn_type = row[2].strip() if len(row) > 2 else "unknown"
        program = row[3].strip() if len(row) > 3 else ""
        remarks = row[11].strip() if len(row) > 11 else ""

        if name == "-0-":
            continue

        entity_type = "unknown"
        type_upper = sdn_type.upper()
        if "INDIVIDUAL" in type_upper:
            entity_type = "individual"
        elif "ENTITY" in type_upper:
            entity_type = "entity"
        elif "VESSEL" in type_upper:
            entity_type = "vessel"
        elif "AIRCRAFT" in type_upper:
            entity_type = "aircraft"

        programs = []
        if program and program != "-0-":
            programs = [p.strip() for p in program.split(";") if p.strip()]

        records[ent_num] = {
            "name": name,
            "entity_type": entity_type,
            "source_ref": ent_num,
            "programs": programs,
            "remarks": remarks,
            "aliases": [],
        }
    return records


def parse_alt_csv(content: str, records: dict) -> dict:
    reader = csv.reader(io.StringIO(content))
    for row in reader:
        if not row or len(row) < 4:
            continue
        ent_num = row[0].strip()
        alias_name = row[3].strip() if len(row) > 3 else ""
        if alias_name and alias_name != "-0-" and ent_num in records:
            records[ent_num]["aliases"].append(alias_name)
    return records


SCHEMA_TYPE_MAP = {
    "person": "individual",
    "organization": "entity",
    "company": "entity",
    "legalentity": "entity",
    "security": "entity",
    "vessel": "vessel",
    "airplane": "aircraft",
    "cryptowallet": "entity",
}


def parse_opensanctions_csv(content: str) -> dict:
    """Parse OpenSanctions targets.simple.csv into {source_ref: record} dict."""
    records = {}
    reader = csv.reader(io.StringIO(content))
    for i, row in enumerate(reader):
        if not row or len(row) < 12:
            continue
        if i == 0 and row[0] == "id":
            continue
        rec_id = row[0].strip()
        schema = row[1].strip().lower() if row[1] else ""
        name = row[2].strip() if row[2] else ""
        aliases_raw = row[3].strip() if len(row) > 3 and row[3] else ""
        programs_raw = row[11].strip() if len(row) > 11 and row[11] else ""

        if not name or name == "-0-":
            continue

        entity_type = SCHEMA_TYPE_MAP.get(schema, "entity")
        aliases = [a.strip() for a in aliases_raw.split(";") if a.strip()]
        programs = [p.strip() for p in programs_raw.split(";") if p.strip()]

        records[rec_id] = {
            "name": name,
            "entity_type": entity_type,
            "source_ref": rec_id,
            "programs": programs,
            "remarks": "",
            "aliases": aliases,
        }
    return records


def fetch_ofac_sdn() -> list[dict]:
    records = {}
    try:
        resp = http_get(OFAC_SDN_URL)
        records = parse_sdn_csv(resp.text)

        try:
            alt_resp = http_get(OFAC_SDN_ALT_URL)
            records = parse_alt_csv(alt_resp.text, records)
        except Exception:
            pass
    except Exception as primary_err:
        records = parse_opensanctions_csv(opensanctions_csv("us_ofac_sdn"))

    result = []
    for ent_num, record in records.items():
        norm = normalise_record(record, "ofac_sdn")
        result.append(norm)
    return result


def fetch(force_refresh: bool = False) -> dict:
    return with_fallback(fetch_ofac_sdn, "ofac_sdn")
