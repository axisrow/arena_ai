"""CLI: fetch both sources, merge, write web/data/models.json."""
from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from .match import merge, name_date
from .sources import arena, openrouter


def finalize(row: dict) -> dict:
    """Pick the release date. The Arena history can't be used (display names changed, old models
    were re-snapshotted in Oct 2026), so: date embedded in the Arena name, else OpenRouter listing date."""
    embedded = name_date(row["arena_name"]) if row["arena_name"] else None
    if embedded:
        date, src = embedded, "arena_name"
    elif row.get("created"):
        date, src = row["created"], "openrouter_created"
    else:
        date, src = None, None
    lic = row.get("license")
    return {
        "name": row["arena_name"] or row["or_name"],
        "variant": row["variant"],
        "org": row.get("org") or "",
        "license": lic,
        "open": None if lic is None else lic.strip().lower() not in ("proprietary", ""),
        "in_arena": row["in_arena"], "in_openrouter": row["in_openrouter"], "match": row["match"],
        "or_id": row.get("or_id"),
        "release_date": date, "release_source": src,
        "context": row.get("context"), "price_in": row.get("price_in"), "price_out": row.get("price_out"),
        "has_free": row.get("has_free", False),
        "input_modalities": row.get("input_modalities", []), "output_modalities": row.get("output_modalities", []),
        "params": row.get("params", []),
        "elo": row["elo"], "arenas": row["arenas"],
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", default="web/data/models.json")
    p.add_argument("--aliases", default="aliases.yml")
    args = p.parse_args()

    arena_models = arena.load()
    or_models = openrouter.load()
    rows = [finalize(r) for r in merge(arena_models, or_models, Path(args.aliases))]

    cats = Counter(c for r in rows for c in r["elo"])
    out = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "categories": [c for c, _ in cats.most_common()],
        "arenas": sorted({a for r in rows for a in r["arenas"]}),
        "models": rows,
    }
    path = Path(args.out)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")))

    both = sum(r["in_arena"] and r["in_openrouter"] for r in rows)
    print(f"{len(rows)} rows: {both} in both, {sum(r['in_arena'] and not r['in_openrouter'] for r in rows)} "
          f"arena-only, {sum(r['in_openrouter'] and not r['in_arena'] for r in rows)} openrouter-only -> {path}")
    print("match types:", dict(Counter(r["match"] for r in rows if r["in_arena"])))


if __name__ == "__main__":
    main()
