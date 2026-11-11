from __future__ import annotations

import json
from datetime import datetime, timezone

from ..http import fetch

URL = "https://openrouter.ai/api/v1/models"


def _price_per_m(value) -> float | None:
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    return round(v * 1e6, 6) if v >= 0 else None  # negative = dynamic pricing


def load() -> list[dict]:
    raw = json.loads(fetch(URL, "openrouter_models.json", "OPENROUTER_API_KEY").read_text())["data"]
    out = []
    for m in raw:
        arch = m.get("architecture") or {}
        pricing = m.get("pricing") or {}
        out.append(
            {
                "or_id": m["id"],
                "or_name": m.get("name") or m["id"],
                "slug": m.get("canonical_slug") or m["id"],
                "created": datetime.fromtimestamp(m["created"], timezone.utc).date().isoformat()
                if m.get("created")
                else None,
                "context": m.get("context_length"),
                "price_in": _price_per_m(pricing.get("prompt")),
                "price_out": _price_per_m(pricing.get("completion")),
                "input_modalities": arch.get("input_modalities") or [],
                "output_modalities": arch.get("output_modalities") or [],
                "params": m.get("supported_parameters") or [],
                "hf_id": m.get("hugging_face_id") or None,
            }
        )
    return out
