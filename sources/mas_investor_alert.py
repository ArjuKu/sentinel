from sources.base import normalise_record, with_fallback, cf_get
from config import MAS_INVESTOR_ALERT_URL

IAL_PAGE_SIZE = 10000


def _clean(value: str) -> str:
    value = (value or "").replace("\uFFFD", "").strip()
    return value


def _split_names(text: str) -> list[str]:
    parts = [p.strip() for p in text.split(";")]
    if len(parts) > 1:
        return parts
    parts = [p.strip() for p in text.split(",")]
    return parts


def fetch_mas_investor_alert() -> list[dict]:
    url = (
        f"{MAS_INVESTOR_ALERT_URL}?json.nl=map&wt=json"
        "&sort=date_dt%20desc,approveddate_dt%20desc"
        f"&q=*:*&rows={IAL_PAGE_SIZE}&start=0"
    )
    resp = cf_get(url, timeout=60)
    data = resp.json()
    docs = data.get("response", {}).get("docs", [])
    if not docs:
        raise Exception("No MAS Investor Alert List entries returned by API")

    records = []
    seen_refs = set()
    for doc in docs:
        doc_id = str(doc.get("id", "")).strip()
        ref = f"mas_ial_{doc_id}"
        if not doc_id or ref in seen_refs:
            continue
        seen_refs.add(ref)

        unreg = doc.get("unregulatedpersons_s") or " ".join(
            str(v) for v in doc.get("unregulatedpersons_t", []) if v
        )
        names = [n for n in (_clean(p) for p in _split_names(unreg)) if n]
        if not names:
            continue

        name = names[0]
        aliases = list(dict.fromkeys(names[1:]))

        for field in ("alternativename_t", "formername_t"):
            for v in doc.get(field, []) or []:
                v = _clean(v)
                if v and v != name and v not in aliases:
                    aliases.append(v)

        date_listed = str(doc.get("date_dt", "") or "")[:10]
        address = _clean(doc.get("address_s", ""))
        notes = _clean(doc.get("notes_s", ""))

        records.append(normalise_record({
            "name": name,
            "aliases": aliases,
            "source_ref": ref,
            "entity_type": "entity",
            "date_listed": date_listed,
            "address": address,
            "remarks": notes,
        }, "mas_investor_alert"))

    if not records:
        raise Exception("No MAS Investor Alert List entries parsed")

    return records


def fetch(force_refresh: bool = False) -> dict:
    return with_fallback(fetch_mas_investor_alert, "mas_investor_alert")
