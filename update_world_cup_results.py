import argparse
import csv
import html
import json
import re
from pathlib import Path
from urllib.request import Request, urlopen


ROOT = Path(__file__).parent
RESULTS_PATH = ROOT / "data" / "results.csv"
FOTMOB_RESULTS_PATH = ROOT / "data" / "world_cup_2026_fotmob_results.json"
FOTMOB_URL = "https://www.fotmob.com/leagues/77/fixtures/world-cup?group=by-round"

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
    fixtures_payload = payload["props"]["pageProps"]["fixtures"]
    fixtures = fixtures_payload.get("allMatches") or []
    if not fixtures:
        fixtures = list(find_fixture_items(fixtures_payload))
    completed = []
    for match_number, fixture in enumerate(fixtures, start=1):
        status = fixture.get("status", {})
        if not status.get("finished") or not status.get("scoreStr"):
            continue
        home_score, away_score = (int(value.strip()) for value in status["scoreStr"].split("-", 1))
        kickoff = status.get("utcTime") or fixture.get("status", {}).get("utcTime") or ""
        completed.append(
            {
                "match": match_number,
                "date": kickoff[:10],
                "home": fixture["home"]["name"],
                "away": fixture["away"]["name"],
                "home_score": home_score,
                "away_score": away_score,
            }
        )
    return completed


def find_fixture_items(value):
    if isinstance(value, dict):
        if {"home", "away", "status"}.issubset(value):
            yield value
            return
        for child in value.values():
            yield from find_fixture_items(child)
    elif isinstance(value, list):
        for child in value:
            yield from find_fixture_items(child)


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
    existing_world_cup_teams = set()
    for row in rows:
        if row["tournament"] != "FIFA World Cup" or not row["date"].startswith("2026-"):
            continue
        teams = frozenset((normalized(row["home_team"]), normalized(row["away_team"])))
        existing_world_cup_teams.add(teams)
        match = result_lookup.get(teams)
        if not match:
            continue
        same_order = normalized(row["home_team"]) == normalized(match["home"])
        row["home_score"] = str(match["home_score"] if same_order else match["away_score"])
        row["away_score"] = str(match["away_score"] if same_order else match["home_score"])
        updated += 1

    for match in matches:
        teams = frozenset((normalized(match["home"]), normalized(match["away"])))
        if teams in existing_world_cup_teams:
            continue
        rows.append(
            {
                "date": match["date"],
                "home_team": match["home"],
                "away_team": match["away"],
                "home_score": str(match["home_score"]),
                "away_score": str(match["away_score"]),
                "tournament": "FIFA World Cup",
                "city": "",
                "country": "",
                "neutral": "TRUE",
            }
        )
        existing_world_cup_teams.add(teams)
        updated += 1

    with RESULTS_PATH.open("w", encoding="utf-8", newline="") as results_file:
        writer = csv.DictWriter(results_file, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    write_fotmob_results(matches)
    return updated


def write_fotmob_results(matches):
    keyed_matches = [match for match in matches if match.get("match")]
    if not keyed_matches:
        return
    FOTMOB_RESULTS_PATH.write_text(
        json.dumps(keyed_matches, indent=2, sort_keys=True),
        encoding="utf-8",
    )


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
