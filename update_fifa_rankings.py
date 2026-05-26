from __future__ import annotations

import csv
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen


OUTPUT_PATH = Path(__file__).parent / "data" / "fifa_rankings.csv"
RANKINGS_URL = "https://inside.fifa.com/fifa-world-ranking/men"
TEAM_CODE_BY_FIFA_NAME = {
    "Mexico": "MEX",
    "South Africa": "RSA",
    "Korea Republic": "KOR",
    "Czechia": "CZE",
    "Canada": "CAN",
    "Bosnia and Herzegovina": "BIH",
    "Qatar": "QAT",
    "Switzerland": "SUI",
    "Brazil": "BRA",
    "Morocco": "MAR",
    "Haiti": "HAI",
    "Scotland": "SCO",
    "USA": "USA",
    "United States": "USA",
    "Paraguay": "PAR",
    "Australia": "AUS",
    "Turkiye": "TUR",
    "Türkiye": "TUR",
    "Germany": "GER",
    "Curaçao": "CUW",
    "Curacao": "CUW",
    "Côte d'Ivoire": "CIV",
    "Cote d'Ivoire": "CIV",
    "Ecuador": "ECU",
    "Netherlands": "NED",
    "Japan": "JPN",
    "Sweden": "SWE",
    "Tunisia": "TUN",
    "Belgium": "BEL",
    "Egypt": "EGY",
    "IR Iran": "IRN",
    "Iran": "IRN",
    "New Zealand": "NZL",
    "Spain": "ESP",
    "Cabo Verde": "CPV",
    "Saudi Arabia": "KSA",
    "Uruguay": "URU",
    "France": "FRA",
    "Senegal": "SEN",
    "Iraq": "IRQ",
    "Norway": "NOR",
    "Argentina": "ARG",
    "Algeria": "ALG",
    "Austria": "AUT",
    "Jordan": "JOR",
    "Portugal": "POR",
    "Congo DR": "COD",
    "DR Congo": "COD",
    "Uzbekistan": "UZB",
    "Colombia": "COL",
    "England": "ENG",
    "Croatia": "CRO",
    "Ghana": "GHA",
    "Panama": "PAN",
}


def main() -> None:
    html = fetch_rankings_html()
    rows = fetch_rankings_from_api(html) or parse_rankings(html)
    wanted_codes = set(TEAM_CODE_BY_FIFA_NAME.values())
    world_cup_rows = [row for row in rows if row["code"] in wanted_codes]
    if len(world_cup_rows) < 40:
        raise RuntimeError(f"Expected most World Cup teams, found {len(world_cup_rows)} rows")
    write_rankings(world_cup_rows)
    print(f"Wrote {len(world_cup_rows)} FIFA ranking rows to {OUTPUT_PATH}")


def fetch_rankings_html() -> str:
    request = Request(
        RANKINGS_URL,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; WorldCupPredictor/1.0)",
            "Accept": "text/html,application/xhtml+xml",
        },
    )
    with urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8", errors="replace")


def parse_rankings(html: str) -> list[dict[str, str]]:
    script_payloads = re.findall(
        r'<script[^>]+type="application/json"[^>]*>(.*?)</script>',
        html,
        flags=re.DOTALL,
    )
    for payload in script_payloads:
        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            continue
        rows = collect_ranking_rows(data)
        if rows:
            return rows

    rows = []
    for name, points in re.findall(r'"name":"([^"]+)".{0,500}?"points":([0-9]+(?:\.[0-9]+)?)', html):
        code = TEAM_CODE_BY_FIFA_NAME.get(name)
        if code:
            rows.append({"code": code, "name": name, "points": points, "rank": ""})
    return dedupe_rows(rows)


def fetch_rankings_from_api(html: str) -> list[dict[str, str]]:
    date_id = latest_date_id(html)
    if not date_id:
        return []

    api_urls = [
        f"https://inside.fifa.com/api/ranking-overview?gender=men&dateId={date_id}",
        f"https://inside.fifa.com/api/ranking-overview?gender=1&dateId={date_id}",
        f"https://inside.fifa.com/api/ranking-overview?rankingType=men&dateId={date_id}",
    ]
    for url in api_urls:
        try:
            payload = fetch_url(url)
            data = json.loads(payload)
        except Exception:
            continue
        rows = rows_from_api_payload(data)
        if rows:
            return rows
    return []


def latest_date_id(html: str) -> str | None:
    marker = "__NEXT_DATA__"
    if marker not in html:
        return None
    start = html.index(">", html.index(marker)) + 1
    end = html.index("</script>", start)
    data = json.loads(html[start:end])
    dates = data["props"]["pageProps"]["pageData"]["ranking"].get("allAvailableDates", [])
    if not dates:
        return None
    return dates[0].get("id")


def fetch_url(url: str) -> str:
    request = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; WorldCupPredictor/1.0)",
            "Accept": "application/json,text/html",
        },
    )
    with urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8", errors="replace")


def rows_from_api_payload(data: dict) -> list[dict[str, str]]:
    rankings = data.get("rankings") or data.get("ranking") or data.get("items") or []
    rows = []
    for item in rankings:
        name = (
            item.get("name")
            or item.get("countryName")
            or item.get("teamName")
            or item.get("team", {}).get("name")
            or item.get("country", {}).get("name")
        )
        code = (
            item.get("countryCode")
            or item.get("code")
            or item.get("team", {}).get("countryCode")
            or item.get("country", {}).get("code")
        )
        points = item.get("totalPoints") or item.get("points") or item.get("rankPoints")
        rank = item.get("rank") or item.get("ranking") or item.get("position")
        code = TEAM_CODE_BY_FIFA_NAME.get(name, code)
        if code and points is not None:
            rows.append(
                {
                    "code": code,
                    "name": name or code,
                    "points": f"{float(points):.2f}",
                    "rank": "" if rank is None else str(int(float(rank))),
                }
            )
    return dedupe_rows(rows)


def collect_ranking_rows(value) -> list[dict[str, str]]:
    rows = []
    if isinstance(value, dict):
        maybe_name = first_string(value, ["name", "teamName", "countryName", "associationName"])
        maybe_points = first_number(value, ["points", "totalPoints", "rankPoints"])
        maybe_rank = first_number(value, ["rank", "ranking", "position"])
        if maybe_name:
            code = TEAM_CODE_BY_FIFA_NAME.get(maybe_name)
            if code and maybe_points is not None:
                rows.append(
                    {
                        "code": code,
                        "name": maybe_name,
                        "points": f"{float(maybe_points):.2f}",
                        "rank": "" if maybe_rank is None else str(int(float(maybe_rank))),
                    }
                )
        for child in value.values():
            rows.extend(collect_ranking_rows(child))
    elif isinstance(value, list):
        for item in value:
            rows.extend(collect_ranking_rows(item))
    return dedupe_rows(rows)


def first_string(mapping: dict, keys: list[str]) -> str | None:
    for key in keys:
        value = mapping.get(key)
        if isinstance(value, str):
            return value
        if isinstance(value, dict):
            nested = first_string(value, ["name", "label", "shortName"])
            if nested:
                return nested
    return None


def first_number(mapping: dict, keys: list[str]) -> float | None:
    for key in keys:
        value = mapping.get(key)
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str) and re.fullmatch(r"[0-9]+(?:\.[0-9]+)?", value):
            return float(value)
    return None


def dedupe_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    by_code = {}
    for row in rows:
        by_code.setdefault(row["code"], row)
    return sorted(by_code.values(), key=lambda item: item["code"])


def write_rankings(rows: list[dict[str, str]]) -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    fetched_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with OUTPUT_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["code", "name", "rank", "points", "fetched_at", "source_url"])
        writer.writeheader()
        for row in rows:
            writer.writerow({**row, "fetched_at": fetched_at, "source_url": RANKINGS_URL})


if __name__ == "__main__":
    main()
