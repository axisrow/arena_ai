"""Tiny cached HTTP helper. Optional tokens come from .env (never hardcoded)."""
from __future__ import annotations

import os
import time
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv()
CACHE_DIR = Path(os.environ.get("ARENA_CACHE_DIR", "data/cache"))
CACHE_TTL = 6 * 3600


def fetch(url: str, name: str, token_env: str | None = None, ttl: int = CACHE_TTL) -> Path:
    """Download `url` to the cache (re-using it while fresh) and return the path."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = CACHE_DIR / name
    if path.exists() and time.time() - path.stat().st_mtime < ttl:
        return path
    headers = {}
    token = os.environ.get(token_env or "")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    with httpx.stream("GET", url, headers=headers, follow_redirects=True, timeout=120) as r:
        r.raise_for_status()
        tmp = path.with_suffix(path.suffix + ".part")
        with tmp.open("wb") as f:
            for chunk in r.iter_bytes():
                f.write(chunk)
        tmp.replace(path)
    return path
