from flask import Flask, render_template

from match_model import build_team_ratings
from schedule_data import MATCH_SCHEDULE

app = Flask(__name__)

LOGO_URL = "https://brandlogos.net/wp-content/uploads/2023/08/2026-FIFA-World-Cup-logo-512x789.png"

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


@app.get("/")
def index():
    return render_template(
        "index.html",
        groups=groups_with_flags(),
        schedule=MATCH_SCHEDULE,
        logo_url=LOGO_URL,
    )


@app.get("/guided")
def guided():
    return render_template(
        "guided.html",
        groups=groups_with_flags(),
        schedule=MATCH_SCHEDULE,
        logo_url=LOGO_URL,
    )


@app.get("/schedule")
def schedule():
    return render_template(
        "schedule.html",
        schedule=MATCH_SCHEDULE,
        schedule_flags=schedule_flag_lookup(),
        logo_url=LOGO_URL,
    )


if __name__ == "__main__":
    app.run(debug=True)
