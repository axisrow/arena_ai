"""Arena (ex-LMArena) leaderboard from the official HF dataset lmarena-ai/leaderboard-dataset."""
from __future__ import annotations

import pandas as pd

from ..http import fetch

BASE = "https://huggingface.co/datasets/lmarena-ai/leaderboard-dataset/resolve/main"
MAIN = "text_style_control"  # Arena's default text leaderboard; all its categories become Elo columns
# Extra arenas: only the "overall" rating of each is kept.
EXTRA = ["vision_style_control", "webdev", "search_style_control", "document_style_control"]


def _parquet(config: str, split: str) -> pd.DataFrame:
    path = fetch(f"{BASE}/{config}/{split}-00000-of-00001.parquet", f"{config}-{split}.parquet", "HF_TOKEN")
    return pd.read_parquet(path)


def _records(df: pd.DataFrame) -> dict[str, dict]:
    out = {}
    for r in df.itertuples():
        out[r.category] = {
            "r": round(float(r.rating), 1),
            "lo": round(float(r.rating_lower), 1),
            "hi": round(float(r.rating_upper), 1),
            "rank": int(r.rank),
            "votes": int(r.vote_count),
        }
    return out


def load() -> list[dict]:
    """Return models. Each model carries `elo` (text categories)
    and `arenas` (overall rating of the other arenas)."""
    latest = _parquet(MAIN, "latest")

    models: dict[str, dict] = {}
    for name, g in latest.groupby("model_name"):
        head = g.iloc[0]
        models[name] = {
            "arena_name": name,
            "org": head.organization,
            "license": head.license,
            "last_update": str(g.leaderboard_publish_date.max()),
            "elo": _records(g),
            "arenas": {},
        }

    for cfg in EXTRA:
        df = _parquet(cfg, "latest")
        df = df[df.category == "overall"]
        label = cfg.removesuffix("_style_control")
        for r in _records_by_model(df).items():
            name, rec = r
            if name in models:
                models[name]["arenas"][label] = rec
            else:  # model only present in this arena (e.g. webdev-only)
                head = df[df.model_name == name].iloc[0]
                models[name] = {
                    "arena_name": name, "org": head.organization, "license": head.license,
                    "last_update": str(head.leaderboard_publish_date),
                    "elo": {}, "arenas": {label: rec},
                }
    return list(models.values())


def _records_by_model(df: pd.DataFrame) -> dict[str, dict]:
    return {
        r.model_name: {
            "r": round(float(r.rating), 1), "lo": round(float(r.rating_lower), 1),
            "hi": round(float(r.rating_upper), 1), "rank": int(r.rank), "votes": int(r.vote_count),
        }
        for r in df.itertuples()
    }
