import re
from bs4 import BeautifulSoup
from sources.base import normalise_record, with_fallback, cf_get


TSFA_URL = "https://sso.agc.gov.sg/Act/TSFA2002?ProvIds=Sc1-"

ITEM2_MARKERS = ("2.", "the following individuals")

DOB_RE = re.compile(r"Date of Birth[:\s]+([0-9]{1,2})\s+([A-Za-z]+)\s+([0-9]{4})")
PASSPORT_RE = re.compile(r"Passport No\.\s*([A-Z0-9]+)", re.IGNORECASE)
CITIZEN_RE = re.compile(r"\(\s*([A-Za-z]+)\s+citizen\s*\)", re.IGNORECASE)

MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11,
    "december": 12,
}


def _clean_text(cell) -> str:
    for tag in cell.find_all("div", class_="amendNote"):
        tag.decompose()
    text = cell.get_text(" ", strip=True)
    text = text.replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def _parse_entry(text: str) -> dict | None:
    text = text.rstrip(";").strip()
    if re.match(r"^\[?\s*Deleted\b", text, re.IGNORECASE):
        return None
    if not text:
        return None

    dob = ""
    m = DOB_RE.search(text)
    if m:
        day, month, year = m.group(1), m.group(2).lower(), m.group(3)
        month_num = MONTHS.get(month)
        if month_num:
            dob = f"{year}-{month_num:02d}-{int(day):02d}"
    else:
        m = re.search(r"Date of Birth:\s*([0-9]{1,2})\s*/\s*([0-9]{1,2})\s*/\s*([0-9]{4})", text)
        if m:
            dob = f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}"

    passport = ""
    m = PASSPORT_RE.search(text)
    if m:
        passport = m.group(1)

    nationality = ""
    m = CITIZEN_RE.search(text)
    if m:
        nationality = m.group(1)

    name = text
    name = DOB_RE.sub("", name)
    name = PASSPORT_RE.sub("", name)
    name = re.sub(r"\(\s*[A-Za-z]+\s+citizen\s*\)", "", name, flags=re.IGNORECASE)
    name = re.sub(r"\(\s*Work Permit No\.[^)]*\)", "", name, flags=re.IGNORECASE)
    name = re.sub(r"\(\s*[^)]*stating[^)]*\)", "", name, flags=re.IGNORECASE)
    name = re.sub(r"\(\)", "", name)
    name = re.sub(r"\s+", " ", name).strip(" .,;")

    aliases = []
    if "@" in name:
        parts = [p.strip() for p in name.split("@")]
        name = parts[0]
        aliases = [p for p in parts[1:] if p]

    return {
        "name": name,
        "aliases": aliases,
        "entity_type": "individual",
        "nationality": nationality,
        "dob": dob,
        "passport": passport,
    }


def fetch_tsfa() -> list[dict]:
    resp = cf_get(TSFA_URL, timeout=40)
    soup = BeautifulSoup(resp.text, "lxml")

    content = soup.find("div", id="legisContent")
    if not content:
        raise Exception("Could not find legisContent on SSO TSFA page")

    item2_block = None
    for td in content.find_all("td", class_="tailSTxt"):
        text = td.get_text(" ", strip=True)
        if text.startswith(ITEM2_MARKERS[0]) and "following individuals" in text.lower():
            item2_block = td
            break

    if not item2_block:
        raise Exception("Could not locate item 2 (individuals) in TSFA First Schedule")

    records = []
    for row in item2_block.find_all("tr"):
        cell = row.find("td", class_="sProvP1")
        if not cell:
            continue
        parsed = _parse_entry(_clean_text(cell))
        if not parsed:
            continue
        slug = re.sub(r"[^A-Za-z]+", "_", parsed["name"]).strip("_").lower()[:40]
        records.append(normalise_record({
            **parsed,
            "programs": ["TSFA First Schedule"],
            "source_ref": f"tsfa_sc1_p2_{slug}",
            "remarks": "Terrorism (Suppression of Financing) Act 2002, First Schedule para 2 (as at current SSO version).",
        }, "tsfa"))

    if not records:
        raise Exception("No TSFA Schedule 1 individuals parsed")

    records.append(normalise_record({
        "name": "All individuals and entities belonging to or associated with the Taliban or with ISIL (Da'esh) / Al-Qaida (UN lists)",
        "entity_type": "unknown",
        "programs": ["TSFA First Schedule"],
        "source_ref": "tsfa_sc1_p1_un_lists",
        "remarks": "TSFA First Schedule para 1 incorporates the UN Taliban List and ISIL (Da'esh) and Al-Qaida Sanctions List. Those names are already screened via the UN Consolidated List source.",
    }, "tsfa"))

    return records


def fetch(force_refresh: bool = False) -> dict:
    return with_fallback(fetch_tsfa, "tsfa")
