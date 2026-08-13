from sources.base import normalise_record, with_fallback, opensanctions_csv
from config import OFAC_NON_SDN_URL, OFAC_NON_SDN_ALT_URL

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
    import csv, io
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


def fetch_ofac_non_sdn() -> list[dict]:
    import csv, io
    from sources.base import http_get

    records = {}
    try:
        resp = http_get(OFAC_NON_SDN_URL)
        reader = csv.reader(io.StringIO(resp.text))
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

            entity_type = "individual" if "individual" in sdn_type.lower() else "entity"

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

        try:
            alt_resp = http_get(OFAC_NON_SDN_ALT_URL)
            reader2 = csv.reader(io.StringIO(alt_resp.text))
            for row in reader2:
                if not row or len(row) < 4:
                    continue
                ent_num = row[0].strip()
                alias_name = row[3].strip() if len(row) > 3 else ""
                if alias_name and alias_name != "-0-" and ent_num in records:
                    records[ent_num]["aliases"].append(alias_name)
        except Exception:
            pass
    except Exception as primary_err:
        records = parse_opensanctions_csv(opensanctions_csv("us_ofac_cons"))

    return [normalise_record(r, "ofac_non_sdn") for r in records.values()]


def fetch(force_refresh: bool = False) -> dict:
    return with_fallback(fetch_ofac_non_sdn, "ofac_non_sdn")
