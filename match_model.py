from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path


DATA_DIR = Path(__file__).parent / "data"
RESULTS_PATH = DATA_DIR / "results.csv"
SHOOTOUTS_PATH = DATA_DIR / "shootouts.csv"
FORMER_NAMES_PATH = DATA_DIR / "former_names.csv"
FIFA_RANKINGS_PATH = DATA_DIR / "fifa_rankings.csv"

# FIFA ranking points from fifa-wc-26-prediction-wip.ipynb.
FIFA_POINTS_BY_NAME = {
    "Mexico": 1681.03,
    "South Africa": 1429.73,
    "South Korea": 1588.66,
    "Czech Republic": 1501.38,
    "Canada": 1556.48,
    "Bosnia and Herzegovina": 1385.84,
    "Qatar": 1454.96,
    "Switzerland": 1649.40,
    "Brazil": 1761.16,
    "Morocco": 1755.87,
    "Haiti": 1291.71,
    "Scotland": 1498.35,
    "USA": 1673.13,
    "Paraguay": 1503.50,
    "Australia": 1580.67,
    "Turkey": 1599.04,
    "Germany": 1730.37,
    "Curacao": 1294.65,
    "Ivory Coast": 1532.98,
    "Ecuador": 1594.78,
    "Netherlands": 1757.87,
    "Japan": 1660.43,
    "Sweden": 1514.77,
    "Tunisia": 1483.05,
    "Belgium": 1734.71,
    "Egypt": 1563.24,
    "Iran": 1615.30,
    "New Zealand": 1281.57,
    "Spain": 1876.40,
    "Cabo Verde": 1366.13,
    "Saudi Arabia": 1421.43,
    "Uruguay": 1673.07,
    "France": 1877.32,
    "Senegal": 1688.99,
    "Iraq": 1447.14,
    "Norway": 1550.94,
    "Argentina": 1874.81,
    "Algeria": 1564.26,
    "Austria": 1593.45,
    "Jordan": 1391.45,
    "Portugal": 1763.83,
    "DR Congo": 1478.35,
    "Uzbekistan": 1465.34,
    "Colombia": 1693.09,
    "England": 1825.97,
    "Croatia": 1717.07,
    "Ghana": 1346.31,
    "Panama": 1540.64,
}

TEAM_NAME_BY_CODE = {
    "MEX": "Mexico",
    "RSA": "South Africa",
    "KOR": "South Korea",
    "CZE": "Czech Republic",
    "CAN": "Canada",
    "BIH": "Bosnia and Herzegovina",
    "QAT": "Qatar",
    "SUI": "Switzerland",
    "BRA": "Brazil",
    "MAR": "Morocco",
    "HAI": "Haiti",
    "SCO": "Scotland",
    "USA": "USA",
    "PAR": "Paraguay",
    "AUS": "Australia",
    "TUR": "Turkey",
    "GER": "Germany",
    "CUW": "Curacao",
    "CIV": "Ivory Coast",
    "ECU": "Ecuador",
    "NED": "Netherlands",
    "JPN": "Japan",
    "SWE": "Sweden",
    "TUN": "Tunisia",
    "BEL": "Belgium",
    "EGY": "Egypt",
    "IRN": "Iran",
    "NZL": "New Zealand",
    "ESP": "Spain",
    "CPV": "Cabo Verde",
    "KSA": "Saudi Arabia",
    "URU": "Uruguay",
    "FRA": "France",
    "SEN": "Senegal",
    "IRQ": "Iraq",
    "NOR": "Norway",
    "ARG": "Argentina",
    "ALG": "Algeria",
    "AUT": "Austria",
    "JOR": "Jordan",
    "POR": "Portugal",
    "COD": "DR Congo",
    "UZB": "Uzbekistan",
    "COL": "Colombia",
    "ENG": "England",
    "CRO": "Croatia",
    "GHA": "Ghana",
    "PAN": "Panama",
}

NAME_ALIASES = {
    "Czechia": "Czech Republic",
    "Côte d'Ivoire": "Ivory Coast",
    "Cote d'Ivoire": "Ivory Coast",
    "Curaçao": "Curacao",
    "Türkiye": "Turkey",
    "Turkiye": "Turkey",
    "Turkey": "Turkey",
    "Korea Republic": "South Korea",
    "South Korea": "South Korea",
    "United States": "USA",
    "United States of America": "USA",
    "United States Virgin Islands": "United States Virgin Islands",
    "Cape Verde": "Cabo Verde",
    "Congo DR": "DR Congo",
    "Democratic Republic of Congo": "DR Congo",
    "Iran": "Iran",
    "IR Iran": "Iran",
}


@dataclass(frozen=True)
class Result:
    played_on: date
    home_name: str
    away_name: str
    home_score: int
    away_score: int
    tournament: str
    neutral: bool
    shootout_winner: str | None = None


def build_team_ratings(team_codes: list[str]) -> dict[str, int]:
    code_to_name = {code: TEAM_NAME_BY_CODE.get(code, code) for code in team_codes}
    tracked_names = set(code_to_name.values())
    fifa_points_by_code = load_fifa_points_by_code()
    ratings = {
        name: fifa_points_to_elo(
            fifa_points_by_code.get(code, FIFA_POINTS_BY_NAME.get(name, 1500))
        )
        for code, name in code_to_name.items()
    }
    results = load_results()
    if not results:
        return {code: ratings[code_to_name[code]] for code in team_codes}

    latest_date = max(result.played_on for result in results)
    for result in sorted(results, key=lambda item: item.played_on):
        if result.home_name not in tracked_names or result.away_name not in tracked_names:
            continue
        update_ratings(ratings, result, latest_date)

    return {code: ratings[code_to_name[code]] for code in team_codes}


def match_win_probability(team_rating: int, opponent_rating: int) -> float:
    return expected_score(team_rating, opponent_rating)


def load_fifa_points_by_code() -> dict[str, float]:
    if not FIFA_RANKINGS_PATH.exists():
        return {}

    points = {}
    with FIFA_RANKINGS_PATH.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if not row.get("code") or not row.get("points"):
                continue
            points[row["code"].upper()] = float(row["points"])
    return points


def load_results() -> list[Result]:
    if not RESULTS_PATH.exists():
        return []

    former_names = load_former_name_map()
    shootout_winners = load_shootout_winners()
    results = []
    with RESULTS_PATH.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if row["home_score"] == "NA" or row["away_score"] == "NA":
                continue
            played_on = datetime.strptime(row["date"], "%Y-%m-%d").date()
            home_name = canonical_name(row["home_team"], former_names)
            away_name = canonical_name(row["away_team"], former_names)
            results.append(
                Result(
                    played_on=played_on,
                    home_name=home_name,
                    away_name=away_name,
                    home_score=int(row["home_score"]),
                    away_score=int(row["away_score"]),
                    tournament=row["tournament"],
                    neutral=row["neutral"].strip().upper() == "TRUE",
                    shootout_winner=shootout_winners.get((played_on, home_name, away_name)),
                )
            )
    return results


def load_former_name_map() -> dict[str, str]:
    name_map = dict(NAME_ALIASES)
    if not FORMER_NAMES_PATH.exists():
        return name_map

    with FORMER_NAMES_PATH.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            current = NAME_ALIASES.get(row["current"], row["current"])
            former = row["former"]
            name_map[former] = current
    return name_map


def load_shootout_winners() -> dict[tuple[date, str, str], str]:
    if not SHOOTOUTS_PATH.exists():
        return {}

    former_names = load_former_name_map()
    winners = {}
    with SHOOTOUTS_PATH.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            played_on = datetime.strptime(row["date"], "%Y-%m-%d").date()
            home_name = canonical_name(row["home_team"], former_names)
            away_name = canonical_name(row["away_team"], former_names)
            winner = canonical_name(row["winner"], former_names)
            winners[(played_on, home_name, away_name)] = winner
    return winners


def canonical_name(name: str, former_names: dict[str, str]) -> str:
    return former_names.get(name, NAME_ALIASES.get(name, name))


def update_ratings(ratings: dict[str, int], result: Result, latest_date: date) -> None:
    home_rating = ratings[result.home_name]
    away_rating = ratings[result.away_name]
    home_advantage = 0 if result.neutral else 55
    expected_home = expected_score(home_rating + home_advantage, away_rating)
    actual_home = actual_home_score(result)
    k_factor = weighted_k_factor(result, latest_date)
    margin = goal_margin_multiplier(abs(result.home_score - result.away_score))
    change = k_factor * margin * (actual_home - expected_home)
    ratings[result.home_name] = round(home_rating + change)
    ratings[result.away_name] = round(away_rating - change)


def actual_home_score(result: Result) -> float:
    if result.home_score > result.away_score:
        return 1.0
    if result.home_score < result.away_score:
        return 0.0
    if result.shootout_winner == result.home_name:
        return 0.55
    if result.shootout_winner == result.away_name:
        return 0.45
    return 0.5


def expected_score(rating_a: int | float, rating_b: int | float) -> float:
    return 1 / (1 + math.pow(10, (rating_b - rating_a) / 400))


def weighted_k_factor(result: Result, latest_date: date) -> float:
    age_days = max((latest_date - result.played_on).days, 0)
    recency_weight = math.exp(-age_days / (365 * 3))
    return 24 * recency_weight * tournament_weight(result.tournament)


def tournament_weight(tournament: str) -> float:
    normalized = tournament.lower()
    if normalized == "fifa world cup":
        return 1.55
    if "qualification" in normalized:
        return 1.18
    if any(token in normalized for token in ["uefa euro", "copa america", "africa cup", "asian cup", "gold cup"]):
        return 1.28
    if "nations league" in normalized:
        return 1.08
    if normalized == "friendly":
        return 0.72
    return 0.95


def goal_margin_multiplier(goal_margin: int) -> float:
    if goal_margin <= 1:
        return 1.0
    return 1 + math.log(goal_margin)


def fifa_points_to_elo(points: float) -> int:
    return round(1500 + (points - 1500) * 0.85)


def poisson_expected_goals(team_rating: int, opponent_rating: int) -> tuple[float, float]:
    diff = team_rating - opponent_rating
    return max(0.15, 1.35 + diff / 520), max(0.15, 1.35 - diff / 520)
