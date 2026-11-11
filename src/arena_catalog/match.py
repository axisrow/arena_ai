"""Join Arena leaderboard rows with OpenRouter models."""
from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path

import yaml
from rapidfuzz import fuzz, process

_PAREN = re.compile(r"\([^)]*\)")
_DATE8 = re.compile(r"(?<!\d)20\d{6}(?!\d)")
_NONALNUM = re.compile(r"[^a-z0-9]+")
_VARIANT = re.compile(r"\(([^)]*)\)")


def variant_of(arena_name: str) -> str:
    """'Claude Opus 5.5 (High)' -> 'High'."""
    m = _VARIANT.search(arena_name)
    return m.group(1).strip() if m else ""


def name_date(arena_name: str) -> str | None:
    """Release date embedded in the model name, e.g. 'Claude 3 Haiku (20240307)' -> '2024-03-07'."""
    m = re.search(r"(?<!\d)(20\d{2})(\d{2})(\d{2})(?!\d)", arena_name)
    if m and 1 <= int(m[2]) <= 12 and 1 <= int(m[3]) <= 31:
        return f"{m[1]}-{m[2]}-{m[3]}"
    return None


def norm(text: str) -> str:
    """Canonical comparison key: no vendor prefix, parentheticals, dates or punctuation."""
    t = text.lower()
    if "/" in t:
        t = t.split("/", 1)[1]
    t = _PAREN.sub(" ", t)
    t = _DATE8.sub(" ", t)
    return _NONALNUM.sub("", t)


def _spaced(text: str) -> str:
    t = _DATE8.sub(" ", _PAREN.sub(" ", text.lower().split("/", 1)[-1]))
    return _NONALNUM.sub(" ", t).strip()


def _digits(text: str) -> tuple[str, ...]:
    return tuple(re.findall(r"\d+", _spaced(text)))


def group_openrouter(models: list[dict]) -> dict[str, dict]:
    """Collapse ':free'/':batch'/... variants into one entry per base id."""
    groups: dict[str, list[dict]] = defaultdict(list)
    for m in models:
        groups[m["or_id"].split(":", 1)[0]].append(m)
    out = {}
    for base, items in groups.items():
        primary = next((i for i in items if ":" not in i["or_id"]), items[0])
        out[base] = {**primary, "or_id": base, "has_free": any(i["or_id"].endswith(":free") for i in items)}
    return out


def _or_keys(m: dict) -> set[str]:
    name = m["or_name"].split(": ", 1)[-1].replace("(free)", "")
    return {k for k in (norm(m["or_id"]), norm(m["slug"]), norm(name)) if k}


def merge(arena: list[dict], openrouter: list[dict], aliases_path: Path | None = None) -> list[dict]:
    aliases = {}
    if aliases_path and aliases_path.exists():
        aliases = yaml.safe_load(aliases_path.read_text()) or {}
    or_models = group_openrouter(openrouter)
    key_index: dict[str, str] = {}
    for base, m in or_models.items():
        for k in _or_keys(m):
            key_index.setdefault(k, base)
    spaced_index = {_spaced(m["or_id"]): base for base, m in or_models.items()}

    rows, used = [], set()
    for a in arena:
        name = a["arena_name"]
        base = aliases.get(name)
        how = "alias" if base in or_models else None
        if how is None:
            base = key_index.get(norm(name))
            how = "exact" if base else None
        if how is None and (best := process.extractOne(_spaced(name), spaced_index, scorer=fuzz.token_sort_ratio, score_cutoff=93)):
            cand = best[2]
            if _digits(name) == _digits(cand):  # never match different version numbers
                base, how = spaced_index[cand], "fuzzy"
        row = {**a, "variant": variant_of(name), "in_arena": True, "in_openrouter": bool(base), "match": how}
        if base:
            used.add(base)
            row.update({k: v for k, v in or_models[base].items() if k != "slug"})
        rows.append(row)

    for base, m in or_models.items():
        if base not in used:
            rows.append(
                {**{k: v for k, v in m.items() if k != "slug"}, "arena_name": None, "org": base.split("/")[0],
                 "license": None, "elo": {}, "arenas": {}, "variant": "",
                 "in_arena": False, "in_openrouter": True, "match": None}
            )
    return rows
