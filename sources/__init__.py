from sources.base import SourceResult, normalise_record
from sources import ofac_sdn, ofac_non_sdn, un_consolidated, dfat, mas_designated, mas_enforcement, tsfa, mas_investor_alert
from matcher import normalize_name, get_phonetic_key
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from config import SOURCE_LABELS


FETCH_FUNCTIONS = {
    "ofac_sdn": ofac_sdn.fetch,
    "ofac_non_sdn": ofac_non_sdn.fetch,
    "un_consolidated": un_consolidated.fetch,
    "dfat": dfat.fetch,
    "mas_designated": mas_designated.fetch,
    "mas_enforcement": mas_enforcement.fetch,
    "tsfa": tsfa.fetch,
    "mas_investor_alert": mas_investor_alert.fetch,
}


def fetch_all_sources(force_refresh: bool = False) -> dict:
    fetch_timestamp = datetime.now(timezone.utc).isoformat()
    sources = {}
    all_records = []

    with ThreadPoolExecutor(max_workers=8) as executor:
        future_map = {
            executor.submit(fn, force_refresh): key
            for key, fn in FETCH_FUNCTIONS.items()
        }
        try:
            for future in as_completed(future_map, timeout=120):
                key = future_map[future]
                try:
                    result = future.result()
                    sources[key] = result
                    all_records.extend(result.get("records", []))
                except Exception as e:
                    sources[key] = SourceResult(
                        source=key,
                        records=[],
                        status="failed",
                        fetched_at=datetime.now(timezone.utc).isoformat(),
                        record_count=0,
                        error=str(e),
                        source_label=SOURCE_LABELS.get(key, key),
                    ).to_dict()
        except Exception:
            for f, key in future_map.items():
                if key not in sources:
                    f.cancel()
                    sources[key] = SourceResult(
                        source=key,
                        records=[],
                        status="failed",
                        fetched_at=datetime.now(timezone.utc).isoformat(),
                        record_count=0,
                        error="Timed out",
                        source_label=SOURCE_LABELS.get(key, key),
                    ).to_dict()

    # Cross-listing: tag UN records with MAS if program matches
    mas_regimes = {
        "DPRK", "IRAN", "LIBYA", "DRC", "SOMALIA", "YEMEN",
        "AL-QAIDA", "TALIBAN", "ISIL", "IRAQ", "AFGHANISTAN",
        "CENTRAL AFRICAN REPUBLIC", "SOUTH SUDAN", "UKRAINE",
        "MYANMAR", "GUINEA-BISSAU", "LEBANON",
    }
    for record in all_records:
        if record.get("source") == "un_consolidated":
            for prog in record.get("programs", []):
                if prog.upper() in mas_regimes:
                    if "MAS" not in record.get("also_listed_by", []):
                        record.setdefault("also_listed_by", []).append("MAS")
                    break

    live_sources = sum(1 for s in sources.values() if s.get("status") == "live")
    cached_sources = sum(1 for s in sources.values() if s.get("status") == "cached")
    failed_sources = sum(1 for s in sources.values() if s.get("status") == "failed")

    return {
        "fetch_timestamp": fetch_timestamp,
        "total_records": len(all_records),
        "source_count": len(sources),
        "live_sources": live_sources,
        "cached_sources": cached_sources,
        "failed_sources": failed_sources,
        "sources": sources,
        "records": all_records,
    }


def build_unified_index(sources_data: dict) -> dict:
    records = sources_data.get("records", [])
    name_pairs = []
    for record in records:
        norm_name = normalize_name(record.get("name", ""))
        record["_norm_name"] = norm_name
        record["_norm_aliases"] = [
            normalize_name(a) for a in record.get("aliases", [])
        ]
        record["_phon_key"] = get_phonetic_key(norm_name)
        if norm_name:
            name_pairs.append((record.get("name", ""), norm_name))

    lookup = {}
    for record in records:
        ref = record.get("source_ref", "")
        if ref:
            lookup[ref] = record

    return {
        "records": records,
        "lookup": lookup,
        "name_pairs": name_pairs,
    }
