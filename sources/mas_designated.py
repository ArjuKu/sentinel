from sources.base import normalise_record, with_fallback, cf_get
from config import MAS_DESIGNATED_URL
from bs4 import BeautifulSoup


MAS_LISTS_URL = "https://www.mas.gov.sg/regulation/anti-money-laundering/targeted-financial-sanctions/lists-of-designated-individuals-and-entities"


def fetch_mas_designated() -> list[dict]:
    resp = cf_get(MAS_LISTS_URL)
    soup = BeautifulSoup(resp.text, "lxml")

    table = soup.find("table")
    if not table:
        raise Exception("Could not find regime table on MAS lists page")

    records = []
    rows = table.find_all("tr")
    for row in rows[1:]:
        cells = row.find_all("td")
        if len(cells) < 3:
            continue

        regime_name = cells[0].get_text(strip=True) if cells[0] else ""
        list_name = cells[2].get_text(strip=True) if len(cells) > 2 else ""

        if not regime_name:
            continue

        # Extract UN list number from the list column
        un_list_num = ""
        import re
        m = re.search(r'UN\s*(\d+)', list_name, re.IGNORECASE)
        if m:
            un_list_num = m.group(1)

        # Also check for links in list column
        list_link = cells[2].find("a") if len(cells) > 2 else None
        un_url = ""
        if list_link and list_link.get("href"):
            un_url = list_link["href"]
        if not un_list_num and un_url:
            m = re.search(r'sanctions/(\d+)', un_url)
            if m:
                un_list_num = m.group(1)

        records.append(normalise_record({
            "programs": [regime_name],
            "name": regime_name,
            "source_ref": f"mas_des_regime_{un_list_num or regime_name[:20]}",
            "remarks": f"Designated under {regime_name} per UN list {list_name}. Actual entries are in the UN Consolidated List cross-referenced by program.",
        }, "mas_designated"))

    if not records:
        raise Exception("No MAS designated regime entries found")

    return records


def fetch(force_refresh: bool = False) -> dict:
    return with_fallback(fetch_mas_designated, "mas_designated")
