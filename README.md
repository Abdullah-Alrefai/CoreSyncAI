# CoreSync AI

A fitness app for tracking workouts, cardio and nutrition, with an AI coach. `streamlit_app.py` is the original single-file version.

## Project layout
- `app.py`: the new app's entry point (Streamlit)
- `core/`: data, business logic and AI. Nothing here imports Streamlit, so a web frontend can reuse it later.
- `ui/`: Streamlit pages and components
- `data/exercises.json`: the built-in exercise library
- `migrations/`: database schema history (Alembic)
- `tests/`: pytest suite

Units: weights in lb, height in inches, distance in miles. Food amounts are stored in grams, because nutrition data is published per 100 g.

## Run locally (Windows)
```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python -m streamlit run app.py
```
The database (`data/coresync.db`) is created and updated automatically on startup. Create an account on the **Sign up** tab.

## Tests
```powershell
.\.venv\Scripts\python -m pytest
```

## Changing the database
After you edit `core/models.py`, generate a migration and commit it:
```powershell
.\.venv\Scripts\alembic revision --autogenerate -m "describe the change"
```
`tests/test_migrations.py` fails if the models and migrations get out of sync.

## Secrets
Put API keys in `.streamlit/secrets.toml` (gitignored) or in environment variables:
```toml
GEMINI_API_KEY = "..."   # AI coach, free from Google AI Studio
USDA_API_KEY = "..."     # food search, optional; DEMO_KEY is used if missing
```
