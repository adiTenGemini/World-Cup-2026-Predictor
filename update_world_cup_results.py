import argparse
import csv
import html
import json
import re
from pathlib import Path
from urllib.request import Request, urlopen


ROOT = Path(__file__).parent
RESULTS_PATH = ROOT / "data" / "results.csv"
FOTMOB_URL = "https://www.fotmob.com/leagues/77/fixtures/world-cup?group=by-date&page=0"

ALIASES = {
    "bosnia & herzegovina": "bosnia and herzegovina",
    "cabo verde": "cape verde",
    "cote d'ivoire": "ivory coast",
    "curaçao": "curacao",
    "czech republic": "czechia",
    "ir iran": "iran",
    "korea republic": "south korea",
    "turkey": "turkiye",
    "united states": "usa",
}


def normalized(name):
    clean = name.strip().lower()
    return ALIASES.get(clean, clean)


def fetch_page():
    request = Request(FOTMOB_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8")


def completed_matches(page_html):
    match = re.search(
        r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
        page_html,
        re.DOTALL,
    )
    if not match:
        raise RuntimeError("FotMob fixture data was not found in the page")
    payload = json.loads(html.unescape(match.group(1)))
    fixtures = payload["props"]["pageProps"]["fixtures"]["allMatches"]
    completed = []
    for fixture in fixtures:
        status = fixture.get("status", {})
        if not status.get("finished") or not status.get("scoreStr"):
            continue
        home_score, away_score = (int(value.strip()) for value in status["scoreStr"].split("-", 1))
        completed.append(
            {
                "home": fixture["home"]["name"],
                "away": fixture["away"]["name"],
                "home_score": home_score,
                "away_score": away_score,
            }
        )
    return completed


def update_results(matches):
    with RESULTS_PATH.open(encoding="utf-8-sig", newline="") as results_file:
        reader = csv.DictReader(results_file)
        fieldnames = reader.fieldnames
        rows = list(reader)

    result_lookup = {
        frozenset((normalized(match["home"]), normalized(match["away"]))): match
        for match in matches
    }
    updated = 0
    for row in rows:
        if row["tournament"] != "FIFA World Cup" or not row["date"].startswith("2026-"):
            continue
        teams = frozenset((normalized(row["home_team"]), normalized(row["away_team"])))
        match = result_lookup.get(teams)
        if not match:
            continue
        same_order = normalized(row["home_team"]) == normalized(match["home"])
        row["home_score"] = str(match["home_score"] if same_order else match["away_score"])
        row["away_score"] = str(match["away_score"] if same_order else match["home_score"])
        updated += 1

    with RESULTS_PATH.open("w", encoding="utf-8", newline="") as results_file:
        writer = csv.DictWriter(results_file, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return updated


def main():
    parser = argparse.ArgumentParser(description="Update World Cup results from FotMob")
    parser.add_argument("--html-file", type=Path, help="Use a previously downloaded FotMob page")
    args = parser.parse_args()
    page_html = args.html_file.read_text(encoding="utf-8") if args.html_file else fetch_page()
    matches = completed_matches(page_html)
    updated = update_results(matches)
    print(f"Updated {updated} completed World Cup matches from FotMob.")


if __name__ == "__main__":
    main()
