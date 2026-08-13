from sources.base import normalise_record, with_fallback, cf_get
from config import MAS_ENFORCEMENT_URL
import re, time
from bs4 import BeautifulSoup


def fetch_mas_enforcement() -> list[dict]:
    records = []
    seen_names = set()
    page = 1

    while True:
        url = f"{MAS_ENFORCEMENT_URL}?page={page}"
        resp = cf_get(url, 30)
        soup = BeautifulSoup(resp.text, "lxml")

        table = soup.find("table")
        if not table:
            break

        rows = table.find_all("tr")
        if len(rows) <= 1:
            break

        found_new = False
        for row in rows[1:]:
            cells = row.find_all("td")
            if len(cells) < 2:
                continue

            name = cells[1].get_text(strip=True) if cells[1] else ""
            issue_date = cells[0].get_text(strip=True) if cells[0] else ""
            action_type = cells[2].get_text(strip=True) if len(cells) > 2 else ""
            title = cells[3].get_text(strip=True) if len(cells) > 3 else ""

            if not name or name in seen_names:
                continue

            seen_names.add(name)
            found_new = True

            records.append(normalise_record({
                "name": name,
                "source_ref": f"mas_enf_{page}_{len(records)}",
                "entity_type": "entity",
                "date_listed": issue_date,
                "programs": [action_type] if action_type else [],
                "remarks": title,
            }, "mas_enforcement"))

        # Check if there's a next page button
        pagination = soup.find(id="MasXbeEnforcementActionPageButtons")
        if pagination:
            next_btn = pagination.find("button", class_="mas-pagination__next")
            if next_btn and next_btn.get("disabled"):
                break

        if not found_new:
            break

        page += 1
        time.sleep(0.3)

    if not records:
        from sources.base import REQUEST_TIMEOUT
        raise Exception("No MAS enforcement entries found")

    return records


def fetch(force_refresh: bool = False) -> dict:
    return with_fallback(fetch_mas_enforcement, "mas_enforcement")
