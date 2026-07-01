import csv
import json
import re
from pathlib import Path
from threading import Lock

from flask import Flask, jsonify, render_template

from match_model import build_team_ratings, poisson_expected_goals
from schedule_data import MATCH_SCHEDULE
from update_world_cup_results import completed_matches, fetch_page, update_results

app = Flask(__name__)

LOGO_URL = "https://brandlogos.net/wp-content/uploads/2023/08/2026-FIFA-World-Cup-logo-512x789.png"
RESULTS_PATH = Path(__file__).parent / "data" / "results.csv"
FOTMOB_RESULTS_PATH = Path(__file__).parent / "data" / "world_cup_2026_fotmob_results.json"
RESULTS_REFRESH_LOCK = Lock()

WORLD_CUP_GROUPS = [
    {
        "id": "A",
        "teams": [
            {"name": "Mexico", "code": "MEX"},
            {"name": "South Africa", "code": "RSA"},
            {"name": "Korea Republic", "code": "KOR"},
            {"name": "Czechia", "code": "CZE"},
        ],
    },
    {
        "id": "B",
        "teams": [
            {"name": "Canada", "code": "CAN"},
            {"name": "Bosnia and Herzegovina", "code": "BIH"},
            {"name": "Qatar", "code": "QAT"},
            {"name": "Switzerland", "code": "SUI"},
        ],
    },
    {
        "id": "C",
        "teams": [
            {"name": "Brazil", "code": "BRA"},
            {"name": "Morocco", "code": "MAR"},
            {"name": "Haiti", "code": "HAI"},
            {"name": "Scotland", "code": "SCO"},
        ],
    },
    {
        "id": "D",
        "teams": [
            {"name": "USA", "code": "USA"},
            {"name": "Paraguay", "code": "PAR"},
            {"name": "Australia", "code": "AUS"},
            {"name": "Turkiye", "code": "TUR"},
        ],
    },
    {
        "id": "E",
        "teams": [
            {"name": "Germany", "code": "GER"},
            {"name": "Curacao", "code": "CUW"},
            {"name": "Cote d'Ivoire", "code": "CIV"},
            {"name": "Ecuador", "code": "ECU"},
        ],
    },
    {
        "id": "F",
        "teams": [
            {"name": "Netherlands", "code": "NED"},
            {"name": "Japan", "code": "JPN"},
            {"name": "Sweden", "code": "SWE"},
            {"name": "Tunisia", "code": "TUN"},
        ],
    },
    {
        "id": "G",
        "teams": [
            {"name": "Belgium", "code": "BEL"},
            {"name": "Egypt", "code": "EGY"},
            {"name": "IR Iran", "code": "IRN"},
            {"name": "New Zealand", "code": "NZL"},
        ],
    },
    {
        "id": "H",
        "teams": [
            {"name": "Spain", "code": "ESP"},
            {"name": "Cabo Verde", "code": "CPV"},
            {"name": "Saudi Arabia", "code": "KSA"},
            {"name": "Uruguay", "code": "URU"},
        ],
    },
    {
        "id": "I",
        "teams": [
            {"name": "France", "code": "FRA"},
            {"name": "Senegal", "code": "SEN"},
            {"name": "Iraq", "code": "IRQ"},
            {"name": "Norway", "code": "NOR"},
        ],
    },
    {
        "id": "J",
        "teams": [
            {"name": "Argentina", "code": "ARG"},
            {"name": "Algeria", "code": "ALG"},
            {"name": "Austria", "code": "AUT"},
            {"name": "Jordan", "code": "JOR"},
        ],
    },
    {
        "id": "K",
        "teams": [
            {"name": "Portugal", "code": "POR"},
            {"name": "Congo DR", "code": "COD"},
            {"name": "Uzbekistan", "code": "UZB"},
            {"name": "Colombia", "code": "COL"},
        ],
    },
    {
        "id": "L",
        "teams": [
            {"name": "England", "code": "ENG"},
            {"name": "Croatia", "code": "CRO"},
            {"name": "Ghana", "code": "GHA"},
            {"name": "Panama", "code": "PAN"},
        ],
    },
]

FLAG_CODES = {
    "MEX": "mx",
    "RSA": "za",
    "KOR": "kr",
    "CZE": "cz",
    "CAN": "ca",
    "BIH": "ba",
    "QAT": "qa",
    "SUI": "ch",
    "BRA": "br",
    "MAR": "ma",
    "HAI": "ht",
    "SCO": "gb-sct",
    "USA": "us",
    "PAR": "py",
    "AUS": "au",
    "TUR": "tr",
    "GER": "de",
    "CUW": "cw",
    "CIV": "ci",
    "ECU": "ec",
    "NED": "nl",
    "JPN": "jp",
    "SWE": "se",
    "TUN": "tn",
    "BEL": "be",
    "EGY": "eg",
    "IRN": "ir",
    "NZL": "nz",
    "ESP": "es",
    "CPV": "cv",
    "KSA": "sa",
    "URU": "uy",
    "FRA": "fr",
    "SEN": "sn",
    "IRQ": "iq",
    "NOR": "no",
    "ARG": "ar",
    "ALG": "dz",
    "AUT": "at",
    "JOR": "jo",
    "POR": "pt",
    "COD": "cd",
    "UZB": "uz",
    "COL": "co",
    "ENG": "gb-eng",
    "CRO": "hr",
    "GHA": "gh",
    "PAN": "pa",
}


def groups_with_flags():
    team_codes = [team["code"] for group in WORLD_CUP_GROUPS for team in group["teams"]]
    ratings = build_team_ratings(team_codes)
    groups = []
    for group in WORLD_CUP_GROUPS:
        teams = []
        for team in group["teams"]:
            flag_code = FLAG_CODES[team["code"]]
            teams.append(
                {
                    **team,
                    "flag_url": f"https://flagcdn.com/w40/{flag_code}.png",
                    "rating": ratings[team["code"]],
                }
            )
        groups.append({**group, "teams": teams})
    return groups


def schedule_flag_lookup():
    lookup = {}
    aliases = {
        "Bosnia & Herzegovina": "Bosnia and Herzegovina",
        "Cape Verde": "Cabo Verde",
        "Curacao": "Curacao",
        "Czech Republic": "Czechia",
        "DR Congo": "Congo DR",
        "Iran": "IR Iran",
        "Ivory Coast": "Cote d'Ivoire",
        "South Korea": "Korea Republic",
        "Turkey": "Turkiye",
        "United States": "USA",
    }
    for group in WORLD_CUP_GROUPS:
        for team in group["teams"]:
            flag_code = FLAG_CODES[team["code"]]
            lookup[team["name"]] = f"https://flagcdn.com/w40/{flag_code}.png"
    for alias, canonical in aliases.items():
        if canonical in lookup:
            lookup[alias] = lookup[canonical]
    return lookup


def normalized_team_name(name):
    aliases = {
        "bosnia & herzegovina": "bosnia and herzegovina",
        "cabo verde": "cape verde",
        "cote d'ivoire": "ivory coast",
        "curaã§ao": "curacao",
        "curaçao": "curacao",
        "czechia": "czech republic",
        "congo dr": "dr congo",
        "ir iran": "iran",
        "korea republic": "south korea",
        "turkiye": "turkey",
        "usa": "united states",
    }
    clean = name.strip().lower()
    return aliases.get(clean, clean)


def fixture_results_by_key():
    results = {}
    with RESULTS_PATH.open(encoding="utf-8-sig", newline="") as result_file:
        for row in csv.DictReader(result_file):
            if row["home_score"] == "NA" or row["away_score"] == "NA":
                continue
            teams = frozenset(
                (normalized_team_name(row["home_team"]), normalized_team_name(row["away_team"]))
            )
            results[(row["date"], teams)] = row
            if row["tournament"] == "FIFA World Cup" and row["date"].startswith("2026-"):
                results[("2026-world-cup", teams)] = row
    return results


def raw_fotmob_results():
    if not FOTMOB_RESULTS_PATH.exists():
        return []
    with FOTMOB_RESULTS_PATH.open(encoding="utf-8") as result_file:
        return json.load(result_file)


def team_lookup(groups):
    lookup = {}
    for group in groups:
        for team in group["teams"]:
            lookup[normalized_team_name(team["name"])] = team
    return lookup


def score_for_fixture(fixture, teams_by_name, results):
    teams = frozenset((normalized_team_name(fixture["team1"]), normalized_team_name(fixture["team2"])))
    result = results.get((fixture["date"], teams)) or results.get(("2026-world-cup", teams))
    if result:
        home_score = int(result["home_score"])
        away_score = int(result["away_score"])
        if normalized_team_name(fixture["team1"]) == normalized_team_name(result["home_team"]):
            return home_score, away_score, "actual"
        return away_score, home_score, "actual"

    team = teams_by_name.get(normalized_team_name(fixture["team1"]))
    opponent = teams_by_name.get(normalized_team_name(fixture["team2"]))
    if not team or not opponent:
        return None

    team_goals, opponent_goals = poisson_expected_goals(team["rating"], opponent["rating"])
    return round(team_goals), round(opponent_goals), "model"


def group_table(group, teams_by_name, results):
    table = {
        team["code"]: {
            "team": team,
            "played": 0,
            "won": 0,
            "drawn": 0,
            "lost": 0,
            "gf": 0,
            "ga": 0,
            "points": 0,
        }
        for team in group["teams"]
    }

    for fixture in MATCH_SCHEDULE:
        if fixture["stage"] != "Group Stage" or fixture["group"] != group["id"]:
            continue
        team = teams_by_name.get(normalized_team_name(fixture["team1"]))
        opponent = teams_by_name.get(normalized_team_name(fixture["team2"]))
        score = score_for_fixture(fixture, teams_by_name, results)
        if not team or not opponent or score is None:
            continue
        team_goals, opponent_goals, _source = score
        home = table[team["code"]]
        away = table[opponent["code"]]
        home["played"] += 1
        away["played"] += 1
        home["gf"] += team_goals
        home["ga"] += opponent_goals
        away["gf"] += opponent_goals
        away["ga"] += team_goals
        if team_goals > opponent_goals:
            home["won"] += 1
            away["lost"] += 1
            home["points"] += 3
        elif team_goals < opponent_goals:
            away["won"] += 1
            home["lost"] += 1
            away["points"] += 3
        else:
            home["drawn"] += 1
            away["drawn"] += 1
            home["points"] += 1
            away["points"] += 1

    return sorted(
        ({**row, "gd": row["gf"] - row["ga"]} for row in table.values()),
        key=lambda row: (row["points"], row["gd"], row["gf"], row["team"]["rating"]),
        reverse=True,
    )


def third_place_assignments(thirds):
    slots = [
        {"key": "m74", "allowed": ["A", "B", "C", "D", "F"]},
        {"key": "m77", "allowed": ["C", "D", "F", "G", "H"]},
        {"key": "m79", "allowed": ["C", "E", "F", "H", "I"]},
        {"key": "m80", "allowed": ["E", "H", "I", "J", "K"]},
        {"key": "m81", "allowed": ["B", "E", "F", "I", "J"]},
        {"key": "m82", "allowed": ["A", "E", "H", "I", "J"]},
        {"key": "m85", "allowed": ["E", "F", "G", "I", "J"]},
        {"key": "m87", "allowed": ["D", "E", "I", "J", "L"]},
    ]

    def search(index, used, assigned):
        if index == len(slots):
            return assigned
        slot = slots[index]
        candidates = [
            team for team in thirds if team["seed"][0] in slot["allowed"] and team["code"] not in used
        ]
        for candidate in candidates:
            solved = search(
                index + 1,
                used | {candidate["code"]},
                {**assigned, slot["key"]: candidate},
            )
            if solved:
                return solved
        return None

    return search(0, set(), {}) or {}


def knockout_seed_lookup(groups, teams_by_name, results):
    tables = {group["id"]: group_table(group, teams_by_name, results) for group in groups}
    seeds = {}
    thirds = []
    for group_id, table in tables.items():
        if len(table) < 3:
            continue
        seeds[f"1{group_id}"] = {**table[0]["team"], "seed": f"{group_id}1"}
        seeds[f"2{group_id}"] = {**table[1]["team"], "seed": f"{group_id}2"}
        thirds.append({**table[2], "team": {**table[2]["team"], "seed": f"{group_id}3"}})

    best_thirds = sorted(
        thirds,
        key=lambda row: (row["points"], row["gd"], row["gf"], row["team"]["rating"]),
        reverse=True,
    )[:8]
    third_assignments = third_place_assignments([row["team"] for row in best_thirds])
    seeds.update(
        {
            "3A/B/C/D/F": third_assignments.get("m74"),
            "3C/D/F/G/H": third_assignments.get("m77"),
            "3C/E/F/H/I": third_assignments.get("m79"),
            "3E/H/I/J/K": third_assignments.get("m80"),
            "3B/E/F/I/J": third_assignments.get("m81"),
            "3A/E/H/I/J": third_assignments.get("m82"),
            "3E/F/G/I/J": third_assignments.get("m85"),
            "3D/E/I/J/L": third_assignments.get("m87"),
        }
    )
    return seeds


def team_seed_lookup(groups, teams_by_name, results):
    seeds = {}
    for group in groups:
        table = group_table(group, teams_by_name, results)
        for index, row in enumerate(table[:3], start=1):
            seeds[normalized_team_name(row["team"]["name"])] = f"{index}{group['id']}"
    return seeds


def slot_accepts_seed(slot, seed):
    if not seed:
        return False
    if re.fullmatch(r"[12][A-L]", slot):
        return slot == seed
    if slot.startswith("3"):
        return seed.startswith("3") and seed[1] in slot[1:].split("/")
    return False


def remap_fotmob_knockout_results(fotmob_results, team_seeds):
    remapped = {}
    used = set()
    round32_fixtures = [
        fixture
        for fixture in MATCH_SCHEDULE
        if fixture["stage"] == "Round of 32"
    ]

    for fixture in round32_fixtures:
        for index, result in enumerate(fotmob_results):
            if index in used:
                continue
            home_seed = team_seeds.get(normalized_team_name(result["home"]))
            away_seed = team_seeds.get(normalized_team_name(result["away"]))
            same_order = (
                slot_accepts_seed(fixture["team1"], home_seed)
                and slot_accepts_seed(fixture["team2"], away_seed)
            )
            reverse_order = (
                slot_accepts_seed(fixture["team1"], away_seed)
                and slot_accepts_seed(fixture["team2"], home_seed)
            )
            if same_order or reverse_order:
                remapped[fixture["match"]] = result
                used.add(index)
                break

    for result in fotmob_results:
        if int(result.get("match", 0)) >= 89:
            remapped[int(result["match"])] = result
    return remapped


def resolve_knockout_team(name, seeds):
    if re.fullmatch(r"[12][A-L]", name) or name.startswith("3"):
        team = seeds.get(name)
        return team["name"] if team else name
    return name


def schedule_with_results():
    """Attach a real score when the local results feed contains one."""
    groups = groups_with_flags()
    teams_by_name = team_lookup(groups)
    results = fixture_results_by_key()
    team_seeds = team_seed_lookup(groups, teams_by_name, results)
    fotmob_results = remap_fotmob_knockout_results(raw_fotmob_results(), team_seeds)
    seeds = knockout_seed_lookup(groups, teams_by_name, results)

    enriched = []
    for fixture in MATCH_SCHEDULE:
        match = dict(fixture)
        fotmob_result = fotmob_results.get(match["match"]) if match["match"] >= 73 else None
        if fotmob_result:
            match["team1"] = fotmob_result["home"]
            match["team2"] = fotmob_result["away"]
            match["actual_team1_goals"] = int(fotmob_result["home_score"])
            match["actual_team2_goals"] = int(fotmob_result["away_score"])
            match["result_source"] = "actual"
            enriched.append(match)
            continue

        if fixture["stage"] != "Group Stage":
            match["team1"] = resolve_knockout_team(fixture["team1"], seeds)
            match["team2"] = resolve_knockout_team(fixture["team2"], seeds)

        score = score_for_fixture(match, teams_by_name, results)
        if score and score[2] == "actual":
            match["actual_team1_goals"], match["actual_team2_goals"], _source = score
            match["result_source"] = "actual"
        else:
            match["result_source"] = "model"
        enriched.append(match)
    return enriched


@app.get("/")
def index():
    return render_template(
        "index.html",
        groups=groups_with_flags(),
        schedule=schedule_with_results(),
        logo_url=LOGO_URL,
    )


@app.get("/guided")
def guided():
    return render_template(
        "guided.html",
        groups=groups_with_flags(),
        schedule=schedule_with_results(),
        logo_url=LOGO_URL,
    )


@app.get("/schedule")
def schedule():
    return render_template(
        "schedule.html",
        schedule=schedule_with_results(),
        schedule_flags=schedule_flag_lookup(),
        logo_url=LOGO_URL,
    )


@app.get("/results")
def results():
    return render_template(
        "results.html",
        groups=groups_with_flags(),
        schedule=schedule_with_results(),
        schedule_flags=schedule_flag_lookup(),
        logo_url=LOGO_URL,
    )


@app.post("/api/results/refresh")
def refresh_results():
    """Fetch completed World Cup matches and return the refreshed schedule."""
    if not RESULTS_REFRESH_LOCK.acquire(blocking=False):
        return jsonify(error="A results refresh is already running."), 409

    try:
        matches = completed_matches(fetch_page())
        updated = update_results(matches)
        return jsonify(
            message=f"Synced {updated} completed match{'es' if updated != 1 else ''} from FotMob.",
            updated=updated,
            schedule=schedule_with_results(),
        )
    except Exception as error:
        app.logger.exception("Unable to refresh results from FotMob")
        return jsonify(error=f"Could not refresh FotMob results: {error}"), 502
    finally:
        RESULTS_REFRESH_LOCK.release()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False, use_reloader=False)
