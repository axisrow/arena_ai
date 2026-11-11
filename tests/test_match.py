from arena_catalog.match import group_openrouter, merge, name_date, norm, variant_of


def _or(id_, name, created="2026-01-01"):
    return {"or_id": id_, "or_name": name, "slug": id_, "created": created, "context": 1000,
            "price_in": 1.0, "price_out": 2.0, "input_modalities": ["text"], "output_modalities": ["text"],
            "params": [], "hf_id": None}


def _arena(name):
    return {"arena_name": name, "org": "x", "license": "Proprietary", "elo": {"overall": {"r": 1500}}, "arenas": {}}


def test_norm_ignores_variants_dates_and_vendor():
    assert norm("Claude Opus 5.5 (High)") == norm("anthropic/claude-opus-5.5") == "claudeopus55"
    assert norm("Claude 3 Haiku (20240307)") == "claude3haiku"


def test_variant_and_date():
    assert variant_of("Claude Opus 5.5 (High)") == "High"
    assert variant_of("GPT-5.5") == ""
    assert name_date("Claude 3 Haiku (20240307)") == "2024-03-07"
    assert name_date("GPT-5.5") is None


def test_group_collapses_suffixes():
    g = group_openrouter([_or("a/m:free", "A: M (free)"), _or("a/m", "A: M")])
    assert list(g) == ["a/m"] and g["a/m"]["has_free"]


def test_merge_exact_and_variants_share_openrouter_model():
    rows = merge([_arena("Claude Opus 5.5 (High)"), _arena("Claude Opus 5.5 (Max)")],
                 [_or("anthropic/claude-opus-5.5", "Anthropic: Claude Opus 5.5")])
    assert [r["or_id"] for r in rows] == ["anthropic/claude-opus-5.5"] * 2
    assert all(r["match"] == "exact" and r["in_openrouter"] for r in rows)


def test_merge_never_matches_different_versions():
    rows = merge([_arena("GPT-5.4")], [_or("openai/gpt-5.5", "OpenAI: GPT-5.5")])
    arena_row, or_row = rows
    assert not arena_row["in_openrouter"] and not or_row["in_arena"]


def test_openrouter_only_rows_are_kept():
    rows = merge([], [_or("foo/bar", "Foo: Bar")])
    assert rows[0]["in_openrouter"] and not rows[0]["in_arena"] and rows[0]["org"] == "foo"
