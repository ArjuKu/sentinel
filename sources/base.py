import requests, json, os, time
from datetime import datetime, timezone
from typing import Literal
from config import USER_AGENT, REQUEST_TIMEOUT, REQUEST_RETRIES, REQUEST_BACKOFF, SOURCE_LABELS

SourceStatus = Literal["live", "cached", "failed"]


class SourceResult:
    def __init__(
        self,
        source: str,
        records: list[dict],
        status: SourceStatus,
        fetched_at: str | None = None,
        record_count: int | None = None,
        error: str | None = None,
        data_url: str | None = None,
        source_label: str | None = None,
    ):
        self.source = source
        self.records = records
        self.status = status
        self.fetched_at = fetched_at or datetime.now(timezone.utc).isoformat()
        self.record_count = record_count if record_count is not None else len(records)
        self.error = error
        self.data_url = data_url
        self.source_label = source_label or SOURCE_LABELS.get(source, source)

    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "source_label": self.source_label,
            "status": self.status,
            "fetched_at": self.fetched_at,
            "record_count": self.record_count,
            "records": self.records,
            "error": self.error,
            "data_url": self.data_url,
        }


def http_get(url: str, timeout: int = REQUEST_TIMEOUT, retries: int = REQUEST_RETRIES, backoff: float = REQUEST_BACKOFF) -> requests.Response:
    headers = {"User-Agent": USER_AGENT}
    last_exception = None
    for attempt in range(retries):
        try:
            resp = requests.get(url, headers=headers, timeout=timeout)
            resp.raise_for_status()
            return resp
        except requests.RequestException as e:
            last_exception = e
            if attempt < retries - 1:
                time.sleep(backoff ** attempt)
    raise last_exception


def opensanctions_csv(dataset: str, timeout: int = 60) -> str:
    """Fetch OpenSanctions targets.simple.csv for a dataset (e.g. 'us_ofac_sdn').
    Resolves the 'latest' index first, then downloads the targets CSV. Returns CSV text."""
    index_url = f"https://data.opensanctions.org/datasets/latest/{dataset}/index.json"
    index_resp = http_get(index_url, timeout=timeout)
    meta = index_resp.json()
    csv_url = None
    for res in meta.get("resources", []):
        if res.get("name") == "targets.simple.csv":
            csv_url = res.get("url")
            break
    if not csv_url:
        raise Exception(f"No targets.simple.csv in OpenSanctions dataset {dataset}")
    resp = http_get(csv_url, timeout=timeout)
    return resp.text


def cf_get(url: str, timeout: int = 30, retries: int = 2, backoff: float = 5) -> requests.Response:
    import cloudscraper
    scraper = cloudscraper.create_scraper()
    last_exception = None
    for attempt in range(retries):
        try:
            resp = scraper.get(url, timeout=timeout)
            resp.raise_for_status()
            return resp
        except requests.RequestException as e:
            last_exception = e
            if attempt < retries - 1:
                time.sleep(backoff)
    raise last_exception


def normalise_record(partial: dict, source: str) -> dict:
    template = {
        "name": "",
        "aliases": [],
        "entity_type": "unknown",
        "source": source,
        "source_label": SOURCE_LABELS.get(source, source),
        "source_ref": "",
        "programs": [],
        "date_listed": "",
        "dob": "",
        "nationality": "",
        "address": "",
        "remarks": "",
        "also_listed_by": [],
        "raw": {},
    }
    record = {**template, **partial}
    record.setdefault("aliases", [])
    record.setdefault("programs", [])
    record.setdefault("also_listed_by", [])
    record.setdefault("raw", {})
    return record


def snapshot_path(source_key: str) -> str:
    base = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
    os.makedirs(base, exist_ok=True)
    return os.path.join(base, f"{source_key}_snapshot.json")


def load_snapshot(source_key: str) -> tuple[list[dict], str | None] | None:
    path = snapshot_path(source_key)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        records = data.get("records", [])
        fetched_at = data.get("fetched_at")
        return records, fetched_at
    except (json.JSONDecodeError, IOError):
        return None


def save_snapshot(source_key: str, records: list[dict], status: str = "live"):
    path = snapshot_path(source_key)
    data = {
        "source": source_key,
        "records": records,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "record_count": len(records),
        "last_status": status,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def with_fallback(fetch_fn, source_key: str) -> dict:
    try:
        records = fetch_fn()
        result = SourceResult(
            source=source_key,
            records=records,
            status="live",
        )
        save_snapshot(source_key, records)
        return result.to_dict()
    except Exception as e:
        snapshot = load_snapshot(source_key)
        if snapshot:
            records, fetched_at = snapshot
            return SourceResult(
                source=source_key,
                records=records,
                status="cached",
                fetched_at=fetched_at,
                error=str(e),
            ).to_dict()
        return SourceResult(
            source=source_key,
            records=[],
            status="failed",
            error=str(e),
        ).to_dict()
