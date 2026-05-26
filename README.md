# World Cup 2026 Predictor

A Flask web app for exploring 2026 FIFA World Cup group-stage predictions. The app combines FIFA ranking points with historical international match results to create team ratings and display the groups in an interactive browser interface.

<img src="https://cdn.prod.website-files.com/689fd0a66c26ce8fe1446c25/69d95f4c71d00684ba1d8e76_FWC26_Ecomm_Photo_Update_B_1000x720-p-800.webp" style="display: block; margin: 0 auto;">

## Features

- View all 12 World Cup 2026 groups with team flags and ratings.
- Explore a guided prediction flow at `/guided`.
- Browse the full 104-match schedule at `/schedule` with filters.
- Build ratings from historical results, shootouts, former team names, and FIFA ranking points.
- Refresh FIFA ranking data from FIFA's men's world ranking page.

## Project Structure

```text
.
|-- app.py                         # Flask routes and World Cup group data
|-- match_model.py                 # Rating, probability, and data-loading logic
|-- schedule_data.py               # Full World Cup 2026 match schedule
|-- update_fifa_rankings.py        # Script to refresh FIFA ranking points
|-- requirements.txt               # Python dependencies
|-- data/                          # Match results, shootouts, names, rankings, archive
|-- static/                        # CSS and browser-side JavaScript
|-- templates/                     # Flask HTML templates
`-- fifa-wc-26-prediction-wip.ipynb # Exploratory notebook
```

## Getting Started

### 1. Create a virtual environment

```bash
python -m venv .venv
```

Activate it:

```bash
# Windows PowerShell
.venv\Scripts\Activate.ps1

# macOS/Linux
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Run the app

```bash
python app.py
```

Then open:

- `http://127.0.0.1:5000/`
- `http://127.0.0.1:5000/guided`
- `http://127.0.0.1:5000/schedule`

## Refresh FIFA Rankings

To fetch the latest FIFA ranking points used by the model:

```bash
python update_fifa_rankings.py
```

This writes `data/fifa_rankings.csv`. If that file is not present, the model falls back to the ranking points embedded in `match_model.py`.

## Model Notes

The predictor uses an Elo-style rating approach:

- FIFA ranking points are converted into initial ratings.
- Historical match results update ratings over time.
- Recent matches receive more weight than older matches.
- Tournaments, qualifiers, friendlies, and major competitions are weighted differently.
- Shootout wins are treated as narrow advantages rather than full regulation wins.

The predictions are for exploration and comparison, not guaranteed outcomes.

## Data

The app reads from CSV files in `data/`, including historical results, shootouts, and former team names. The included data powers the rating updates and team-name normalization used by the model.
