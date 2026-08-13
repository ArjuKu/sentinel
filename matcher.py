import unicodedata
import re
from config import FUZZY_THRESHOLD, HIT_THRESHOLD, POTENTIAL_THRESHOLD

LEGAL_SUFFIXES = [
    r'\bPTE\.?\s+LTD\.?\b', r'\bLTD\.?\b', r'\bLIMITED\b', r'\bLLC\.?\b', r'\bL\.L\.C\.\b',
    r'\bINC\.?\b', r'\bINCORPORATED\b', r'\bCORP\.?\b', r'\bCORPORATION\b',
    r'\bGMBH\b', r'\bAG\b', r'\bSA\b', r'\bSARL\b', r'\bPLC\b',
    r'\bSDN\s+BHD\b', r'\bBHD\b', r'\bCO\.?\b', r'\bCOMPANY\b',
    r'\bAND\s+COMPANY\b', r'\b&\s+CO\b', r'\bLLP\.?\b', r'\bL\.P\.\b', r'\bLP\b',
    r'\bS\.A\.S\.\b', r'\bSPA\b', r'\bS\.R\.L\.\b', r'\bNV\b', r'\bBV\b',
    r'\bPT\b', r'\bAO\b', r'\bOOO\b', r'\bKK\b', r'\bAB\b', r'\bAS\b',
    r'\bA/S\b', r'\bAPS\b',
    r'\bFZE\b', r'\bFZCO\b', r'\bWLL\b', r'\bJSC\b', r'\bPJSC\b',
    r'\bOAO\b', r'\bZAO\b', r'\bOY\b',
]

HONORIFICS = [
    r'\bMR\b', r'\bMRS\b', r'\bMS\b', r'\bMISS\b', r'\bDR\b', r'\bPROF\b',
    r'\bSHEIKH\b', r'\bHAJJI\b', r'\bGENERAL\b', r'\bCOL\b', r'\bCOLONEL\b',
    r'\bMAJ\b', r'\bMAJOR\b', r'\bCAPT\b', r'\bCAPTAIN\b', r'\bLT\b', r'\bLIEUTENANT\b',
    r'\bSGT\b', r'\bSERGEANT\b', r'\bADM\b', r'\bADMIRAL\b',
    r'\bHON\b', r'\bHONOURABLE\b', r'\bRT\b', r'\bREV\b', r'\bREVEREND\b',
    r'\bPRESIDENT\b', r'\bCEO\b', r'\bDIRECTOR\b', r'\bMANAGING\b',
]

BRACKET_PATTERN = re.compile(r'\([^)]*\)|\[[^\]]*\]|\{[^}]*\}')
SEPARATOR_PATTERN = re.compile(r'[-./,\'’]+')
WHITESPACE_PATTERN = re.compile(r'\s+')
SUFFIX_PATTERN = re.compile('|'.join(LEGAL_SUFFIXES), re.IGNORECASE)
HONORIFIC_PATTERN = re.compile('|'.join(HONORIFICS), re.IGNORECASE)


def normalize_name(raw: str) -> str:
    if not raw:
        return ""
    text = unicodedata.normalize("NFKD", raw)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.upper()
    text = BRACKET_PATTERN.sub("", text)
    text = SUFFIX_PATTERN.sub("", text)
    text = HONORIFIC_PATTERN.sub("", text)
    text = SEPARATOR_PATTERN.sub(" ", text)
    text = WHITESPACE_PATTERN.sub(" ", text)
    text = text.strip()
    return text


def get_phonetic_key(name: str) -> str:
    try:
        from jellyfish import metaphone
        return metaphone(name) or ""
    except ImportError:
        return ""


def token_overlap_sufficient(query_norm: str, matched_norm: str) -> bool:
    """A HIT requires a substantial name match. When both the query and the
    matched value (record name or alias) are multi-word, require at least two
    tokens in common so a single shared leading word (e.g. 'GLOBAL') does not
    produce a HIT. Single-token values are exempt (exact single-word matches
    and short aliases should still match)."""
    q_tokens = set(query_norm.split())
    m_tokens = set(matched_norm.split())
    if len(q_tokens) < 2 or len(m_tokens) < 2:
        return True
    return len(q_tokens & m_tokens) >= 2


def should_skip(query_norm: str, record_norm: str) -> bool:
    if not query_norm or not record_norm:
        return True
    if query_norm[0] not in record_norm:
        len_diff = abs(len(query_norm) - len(record_norm))
        max_len = max(len(query_norm), len(record_norm))
        if max_len > 0 and len_diff / max_len > 0.4:
            return True
    return False


def match_single(query: str, records: list[dict], threshold: float = None, enable_phonetic: bool = True) -> dict:
    if threshold is None:
        threshold = FUZZY_THRESHOLD

    from rapidfuzz import fuzz

    query_norm = normalize_name(query)
    query_phon = get_phonetic_key(query_norm) if enable_phonetic else ""

    matches = []

    for record in records:
        record_norm = record.get("_norm_name", "")
        record_aliases = record.get("_norm_aliases", [])
        record_phon = record.get("_phon_key", "")

        best_confidence = 0
        best_strategy = ""
        best_matched_name = ""
        is_alias = False

        if not record_norm:
            continue

        # Strategy 1: Exact
        if query_norm == record_norm:
            best_confidence = 100
            best_strategy = "exact"
            best_matched_name = record.get("name", "")
            is_alias = False

        # Strategy 2: Alias
        if best_confidence < 100:
            for alias in record_aliases:
                if query_norm == alias:
                    best_confidence = 100
                    best_strategy = "alias"
                    best_matched_name = alias
                    is_alias = True
                    break

        # Strategy 3: Substring
        if best_confidence < 90:
            if len(query_norm) >= 5 and len(record_norm) >= 5:
                if query_norm in record_norm or record_norm in query_norm:
                    best_confidence = 90
                    best_strategy = "substring"
                    best_matched_name = record.get("name", "")

        if best_confidence < threshold:
            if should_skip(query_norm, record_norm):
                continue

            # Strategy 4: Fuzzy (token_set_ratio)
            ratio = int(round(fuzz.token_set_ratio(query_norm, record_norm)))
            if ratio >= threshold:
                best_confidence = ratio
                best_strategy = "fuzzy"
                best_matched_name = record.get("name", "")

            # Also check aliases
            if best_confidence < 100:
                for alias in record_aliases:
                    alias_ratio = int(round(fuzz.token_set_ratio(query_norm, alias)))
                    if alias_ratio >= threshold and alias_ratio > best_confidence:
                        best_confidence = alias_ratio
                        best_strategy = "fuzzy"
                        best_matched_name = alias
                        is_alias = True

            # Strategy 5: Phonetic
            if best_confidence < threshold and query_phon and record_phon:
                if query_phon == record_phon:
                    fuzzy_score = fuzz.token_set_ratio(query_norm, record_norm)
                    phon_conf = 80 + int((fuzzy_score - 70) * 9 / 30) if fuzzy_score >= 70 else 80
                    phon_conf = min(phon_conf, 89)
                    if phon_conf > best_confidence and phon_conf >= POTENTIAL_THRESHOLD:
                        best_confidence = phon_conf
                        best_strategy = "phonetic"
                        best_matched_name = record.get("name", "")

        if best_confidence >= POTENTIAL_THRESHOLD:
            matched_norm = best_matched_name if is_alias else record_norm
            if not token_overlap_sufficient(query_norm, matched_norm):
                best_confidence = min(best_confidence, HIT_THRESHOLD - 1)
            matches.append({
                "record": record,
                "strategy": best_strategy,
                "confidence": best_confidence,
                "matched_name": best_matched_name,
                "is_alias": is_alias,
            })

    matches.sort(key=lambda m: m["confidence"], reverse=True)

    verdict = "NO HIT"
    top_confidence = 0
    if matches:
        top_confidence = matches[0]["confidence"]
        if top_confidence >= HIT_THRESHOLD:
            verdict = "HIT"
        elif top_confidence >= POTENTIAL_THRESHOLD:
            verdict = "POTENTIAL HIT"

    return {
        "query": query,
        "query_normalized": query_norm,
        "query_phonetic": query_phon,
        "total_records_screened": len(records),
        "match_count": len(matches),
        "top_confidence": top_confidence,
        "matches": matches,
        "verdict": verdict,
    }


def match_batch(queries: list[str], records: list[dict], threshold: float = None, enable_phonetic: bool = True, progress_callback=None) -> dict:
    results = []
    hit_count = 0
    potential_count = 0
    no_hit_count = 0

    for i, query in enumerate(queries):
        result = match_single(query, records, threshold, enable_phonetic)
        results.append(result)
        if result["verdict"] == "HIT":
            hit_count += 1
        elif result["verdict"] == "POTENTIAL HIT":
            potential_count += 1
        else:
            no_hit_count += 1

        if progress_callback:
            progress_callback(i + 1, len(queries))

    return {
        "total": len(queries),
        "hit_count": hit_count,
        "potential_count": potential_count,
        "no_hit_count": no_hit_count,
        "results": results,
    }
