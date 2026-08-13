import requests, io, re, openpyxl
from sources.base import normalise_record, with_fallback, cf_get
from config import DFAT_LANDING_URL


DFAT_XLSX_URL = "https://www.dfat.gov.au/sites/default/files/Australian_Sanctions_Consolidated_List.xlsx"
DFAT_MIRROR_URL = "https://sanctionslists.org/wp-content/uploads/2026/02/Australian_Sanctions_Consolidated_List.xlsx"


def fetch_dfat() -> list[dict]:
    xlsx_data = None

    # Try direct XLSX URL first
    for url in [DFAT_XLSX_URL, DFAT_MIRROR_URL]:
        try:
            resp = cf_get(url, timeout=60)
            xlsx_data = resp.content
            break
        except Exception:
            continue

    if xlsx_data is None:
        raise Exception("Could not download DFAT XLSX from any URL")

    wb = openpyxl.load_workbook(io.BytesIO(xlsx_data), read_only=True, data_only=True)
    ws = wb.active

    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        wb.close()
        return []

    header = [str(c).strip() if c else "" for c in rows[0]]

    name_col = type_col = ref_col = alias_col = remarks_col = None
    for i, h in enumerate(header):
        hl = h.lower()
        if hl in ("type",) and type_col is None:
            type_col = i
        elif "name type" in hl or hl == "name type":
            alias_col = i
        elif hl in ("reference",) or hl == "reference":
            ref_col = i
        elif hl in ("additional information", "remarks", "comment", "additional") and remarks_col is None:
            remarks_col = i
        elif name_col is None and "name" in hl and "type" not in hl:
            name_col = i

    if name_col is None:
        for i, h in enumerate(header):
            if "name" in h.lower():
                name_col = i
                break
    if name_col is None:
        raise Exception("Could not find name column in DFAT XLSX")

    groups = {}
    for row in rows[1:]:
        if not row or not any(row):
            continue
        ref = str(row[ref_col]).strip() if ref_col is not None and row[ref_col] else ""
        name = str(row[name_col]).strip() if row[name_col] else ""
        if not name:
            continue
        name_type = str(row[alias_col]).strip().lower() if alias_col is not None and row[alias_col] else ""
        is_alias = "alias" in name_type or "aka" in name_type

        group_key = ref or name
        if group_key not in groups:
            groups[group_key] = {
                "name": name,
                "aliases": [],
                "entity_type": "entity",
                "source_ref": ref,
                "programs": [],
                "remarks": "",
            }
            if type_col is not None and row[type_col]:
                type_val = str(row[type_col]).strip().lower()
                if "individual" in type_val:
                    groups[group_key]["entity_type"] = "individual"
                elif "entity" in type_val:
                    groups[group_key]["entity_type"] = "entity"

        if is_alias and name != groups[group_key]["name"]:
            if name not in groups[group_key]["aliases"]:
                groups[group_key]["aliases"].append(name)

        if remarks_col is not None and row[remarks_col]:
            groups[group_key]["remarks"] = str(row[remarks_col]).strip()

    wb.close()
    return [normalise_record(r, "dfat") for r in groups.values()]


def fetch(force_refresh: bool = False) -> dict:
    return with_fallback(fetch_dfat, "dfat")
