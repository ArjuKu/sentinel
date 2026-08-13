import xml.etree.ElementTree as ET
import io
from sources.base import http_get, normalise_record, with_fallback
from config import UN_CONSOLIDATED_URL


def parse_un_xml(content: bytes) -> list[dict]:
    root = ET.fromstring(content)
    records = []

    ns = {
        "ns": "https://www.un.org/resources/sc/consolidated-list"
    }

    individuals = root.find("INDIVIDUALS")
    if individuals is not None:
        for individual in individuals.findall("INDIVIDUAL"):
            record = parse_individual(individual)
            if record:
                records.append(record)

    entities = root.find("ENTITIES")
    if entities is not None:
        for entity in entities.findall("ENTITY"):
            record = parse_entity(entity)
            if record:
                records.append(record)

    return records


def text_of(parent, tag: str) -> str:
    el = parent.find(tag)
    return el.text.strip() if el is not None and el.text else ""


def parse_individual(el) -> dict | None:
    parts = []
    for tag in ("FIRST_NAME", "SECOND_NAME", "THIRD_NAME", "FOURTH_NAME"):
        val = text_of(el, tag)
        if val:
            parts.append(val)
    if not parts:
        return None
    name = " ".join(parts)

    aliases = []
    alias_container = el.find("INDIVIDUAL_ALIAS")
    if alias_container is not None:
        for alias in alias_container.findall("ALIAS_NAME"):
            alias_text = alias.text.strip() if alias.text else ""
            if alias_text:
                aliases.append(alias_text)

    programs = []
    list_type = text_of(el, "UN_LIST_TYPE")
    if list_type:
        programs.append(list_type)

    dob = ""
    dob_container = el.find("INDIVIDUAL_DATE_OF_BIRTH")
    if dob_container is not None:
        dob = text_of(dob_container, "DATE")

    nationality = text_of(el, "NATIONALITY")

    address = ""
    addr_container = el.find("INDIVIDUAL_ADDRESS")
    if addr_container is not None:
        parts = []
        for tag in ("STREET", "CITY", "COUNTRY"):
            val = text_of(addr_container, tag)
            if val:
                parts.append(val)
        address = ", ".join(parts)

    remarks = text_of(el, "COMMENTS1")

    return normalise_record({
        "name": name,
        "aliases": aliases,
        "entity_type": "individual",
        "source_ref": text_of(el, "DATAID"),
        "programs": programs,
        "date_listed": text_of(el, "LISTED_ON"),
        "dob": dob,
        "nationality": nationality,
        "address": address,
        "remarks": remarks,
        "raw": {
            "reference_number": text_of(el, "REFERENCE_NUMBER"),
            "un_list_type": list_type,
        },
    }, "un_consolidated")


def parse_entity(el) -> dict | None:
    name = text_of(el, "FIRST_NAME")
    if not name:
        return None

    aliases = []
    alias_container = el.find("ENTITY_ALIAS")
    if alias_container is not None:
        for alias in alias_container.findall("ALIAS_NAME"):
            alias_text = alias.text.strip() if alias.text else ""
            if alias_text:
                aliases.append(alias_text)

    programs = []
    list_type = text_of(el, "UN_LIST_TYPE")
    if list_type:
        programs.append(list_type)

    address = ""
    addr_container = el.find("ENTITY_ADDRESS")
    if addr_container is not None:
        parts = []
        for tag in ("STREET", "CITY", "COUNTRY"):
            val = text_of(addr_container, tag)
            if val:
                parts.append(val)
        address = ", ".join(parts)

    remarks = text_of(el, "COMMENTS1")

    return normalise_record({
        "name": name,
        "aliases": aliases,
        "entity_type": "entity",
        "source_ref": text_of(el, "DATAID"),
        "programs": programs,
        "date_listed": text_of(el, "LISTED_ON"),
        "address": address,
        "remarks": remarks,
        "raw": {
            "reference_number": text_of(el, "REFERENCE_NUMBER"),
            "un_list_type": list_type,
        },
    }, "un_consolidated")


def fetch_un_consolidated() -> list[dict]:
    resp = http_get(UN_CONSOLIDATED_URL)
    return parse_un_xml(resp.content)


def fetch(force_refresh: bool = False) -> dict:
    return with_fallback(fetch_un_consolidated, "un_consolidated")
