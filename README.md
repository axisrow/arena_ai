# arena_ai

Catalog that merges the [Arena](https://arena.ai) (ex-LMArena) leaderboard with the [OpenRouter](https://openrouter.ai) model list:
release date, Elo per category (+ rank, votes, CI), price, context, modalities, supported parameters, license / organization,
with sortable columns and filters. Static page, no build step.

## Usage
```bash
python -m venv .venv && . .venv/bin/activate
pip install -e '.[dev]'
cp .env.example .env          # optional tokens (OPENROUTER_API_KEY, HF_TOKEN); public endpoints work without
python -m arena_catalog.build # fetch + merge -> web/data/models.json
python -m http.server -d web  # open http://localhost:8000
pytest
```
Filter/sort state is stored in the URL hash, so views can be shared.

## Data
- **Arena**: official HF dataset `lmarena-ai/leaderboard-dataset` (`text_style_control` with all categories; `overall` of
  vision / webdev / search / document). Arena has no public API.
- **OpenRouter**: `GET /api/v1/models`. `:free` / `:batch` variants are collapsed into one entry (prices of the base model).
- **Matching** (`src/arena_catalog/match.py`): normalized names, then a guarded fuzzy match (version numbers must be equal),
  then manual overrides in `aliases.yml`. Several Arena variants ("High", "Max") share one OpenRouter model; use
  "best variant per model" to dedupe. Unmatched models from both sides are kept and tagged.
- **Release date**: Arena's history cannot give it (names change, old models were re-snapshotted), so it is the date embedded
  in the Arena name (e.g. `20250219`), else the OpenRouter *listing* date (not always the true release). Source is in the tooltip.

## Not included (and why)
- *Price per solved task* (shown on arena.ai) and *OpenRouter token-usage popularity*: not in the HF dataset or the OpenRouter
  API, and arena.ai could not be fetched from the dev sandbox, so they were not implemented rather than guessed.
