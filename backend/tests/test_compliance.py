"""Tests for the deterministic compliance checks + refinement routing."""
from __future__ import annotations

from typing import Any

import pytest

from app.schemas import Brief
from app.services.compliance import (
    ComplianceIssue,
    check_compliance,
    format_issues_for_retry,
    issues_by_persona,
)
from app.services.council import _plan_refinement


@pytest.fixture
def vi_brief() -> Brief:
    return Brief(
        mood="hoài niệm, chậm rãi",
        genre="V-pop ballad",
        language="vi",
        duration_sec=210,
        references=["Hà Anh Tuấn — Tháng Tư"],
    )


@pytest.fixture
def en_brief() -> Brief:
    return Brief(
        mood="uplifting",
        genre="english pop ballad",
        language="en",
        duration_sec=200,
    )


def _clean_contributions(brief: Brief) -> dict[str, dict[str, Any]]:
    """A council output that should pass every deterministic check.

    The math: 60 bars × 4 beats × 60s / 82 BPM ≈ 175.6s vs 210s target →
    delta = 16% which is just inside the 20% tolerance, but we want a
    margin so the test isn't fragile. Picking 70 bars at 80 BPM gives
    210s exactly.
    """
    return {
        "theorist": {
            "key": "E minor",
            "tempo_bpm": 80,
            "time_signature": "4/4",
            "bar_count_total": 70,
            "chord_progression_per_section": {
                "intro": ["Em", "Cmaj7", "G", "D"],
                "verse": ["Em", "Bm/D", "Cmaj7", "G/B"],
                "pre_chorus": ["Am", "Bm", "C", "D"],
                "chorus": ["Em", "C", "G", "D", "Em", "D", "C", "B7"],
                "bridge": ["Am", "F", "C", "G"],
                "outro": ["Em", "Cmaj7", "G", "D"],
            },
        },
        "composer": {
            "song_form": [
                "intro", "verse", "pre_chorus", "chorus",
                "verse", "chorus", "bridge", "chorus", "outro",
            ],
            "section_bars": {
                "intro": 4, "verse": 8, "pre_chorus": 4,
                "chorus": 8, "bridge": 8, "outro": 4,
            },
            "peak_section": "chorus_final",
            "hook_recipe_used": "recipe-2-step-down-rest",
        },
        "arranger": {
            "energy_per_section": {
                "intro": 2,
                "verse_1": 4,
                "pre_chorus": 6,
                "chorus_1": 7,
                "verse_2": 4,
                "chorus_2": 7,
                "bridge": 3,
                "chorus_final": 9,
                "outro": 2,
            },
            "per_section_textures": {
                "chorus": "kick + snare full kit",
                "chorus_final": "kick + snare full kit + string layer + modulation +1",
            },
        },
        "producer": {
            "suno_style_string": (
                "v-pop ballad, 80 bpm, e minor, felt piano, nylon guitar, "
                "warm vocal, plate reverb, ha anh tuan style"
            ),
            "references": [
                "Hà Anh Tuấn — Tháng Tư là lời nói dối",
                "Vũ. — Lạ Lùng",
            ],
        },
    }


def test_check_compliance_clean(vi_brief: Brief) -> None:
    issues = check_compliance(vi_brief, _clean_contributions(vi_brief))
    assert issues == [], f"Expected clean output but got: {[i.code for i in issues]}"


def test_theorist_bar_duration_math_flagged(vi_brief: Brief) -> None:
    contributions = _clean_contributions(vi_brief)
    # 70 bars at 200 BPM = 84s — way under 210s target.
    contributions["theorist"]["tempo_bpm"] = 200
    issues = check_compliance(vi_brief, contributions)
    codes = {i.code for i in issues}
    assert "bar_duration_math" in codes
    assert all(i.persona_role == "theorist" for i in issues if i.code == "bar_duration_math")


def test_theorist_bar_duration_math_within_tolerance(vi_brief: Brief) -> None:
    contributions = _clean_contributions(vi_brief)
    # 70 bars at 88 BPM = 191s vs 210s target = 9% delta, inside ±20%.
    contributions["theorist"]["tempo_bpm"] = 88
    issues = check_compliance(vi_brief, contributions)
    codes = {i.code for i in issues}
    assert "bar_duration_math" not in codes


def test_theorist_chord_too_few_flagged(vi_brief: Brief) -> None:
    contributions = _clean_contributions(vi_brief)
    contributions["theorist"]["chord_progression_per_section"]["verse"] = ["Em", "Cmaj7"]
    issues = check_compliance(vi_brief, contributions)
    assert any(i.code == "chord_progression_too_short" for i in issues)


def test_theorist_chord_roman_flagged(vi_brief: Brief) -> None:
    contributions = _clean_contributions(vi_brief)
    contributions["theorist"]["chord_progression_per_section"]["chorus"] = [
        "i", "VI", "III", "VII"
    ]
    issues = check_compliance(vi_brief, contributions)
    assert any(i.code == "chord_roman_numeral" for i in issues)


def test_theorist_key_missing_root_flagged(vi_brief: Brief) -> None:
    contributions = _clean_contributions(vi_brief)
    contributions["theorist"]["key"] = "minor"
    issues = check_compliance(vi_brief, contributions)
    assert any(i.code == "key_missing_root" for i in issues)


def test_composer_peak_in_verse_flagged(vi_brief: Brief) -> None:
    contributions = _clean_contributions(vi_brief)
    contributions["composer"]["peak_section"] = "verse_1"
    issues = check_compliance(vi_brief, contributions)
    codes_by_role = {(i.persona_role, i.code) for i in issues}
    assert ("composer", "peak_in_verse_1") in codes_by_role


def test_composer_hook_recipe_missing_flagged(vi_brief: Brief) -> None:
    contributions = _clean_contributions(vi_brief)
    contributions["composer"]["hook_recipe_used"] = ""
    issues = check_compliance(vi_brief, contributions)
    assert any(i.code == "hook_recipe_missing" for i in issues)


def test_composer_hook_recipe_unknown_flagged(vi_brief: Brief) -> None:
    contributions = _clean_contributions(vi_brief)
    contributions["composer"]["hook_recipe_used"] = "recipe-99-magic-thing"
    issues = check_compliance(vi_brief, contributions)
    assert any(i.code == "hook_recipe_unknown" for i in issues)


def test_composer_hook_recipe_normalisation(vi_brief: Brief) -> None:
    """Recipe name with case + punctuation variation is still accepted."""
    contributions = _clean_contributions(vi_brief)
    contributions["composer"]["hook_recipe_used"] = "Recipe 2 Step Down Rest"
    issues = check_compliance(vi_brief, contributions)
    composer_issues = [i for i in issues if i.persona_role == "composer"]
    assert all(i.code != "hook_recipe_unknown" for i in composer_issues)


def test_composer_section_bars_math_flagged(vi_brief: Brief) -> None:
    contributions = _clean_contributions(vi_brief)
    # Form sums to ~52 bars at 80 BPM = 156s vs 210s target = 26% delta.
    contributions["composer"]["section_bars"] = {
        "intro": 2, "verse": 6, "pre_chorus": 2,
        "chorus": 6, "bridge": 4, "outro": 2,
    }
    issues = check_compliance(vi_brief, contributions)
    assert any(i.code == "section_bars_math" for i in issues)


def test_arranger_no_strip_down_flagged(vi_brief: Brief) -> None:
    contributions = _clean_contributions(vi_brief)
    contributions["arranger"]["energy_per_section"] = {
        "intro": 5, "verse_1": 6, "pre_chorus": 7,
        "chorus_1": 8, "verse_2": 6, "chorus_2": 8,
        "bridge": 7, "chorus_final": 9, "outro": 5,
    }
    issues = check_compliance(vi_brief, contributions)
    assert any(i.code == "no_strip_down" for i in issues)


def test_arranger_final_chorus_flat_flagged(vi_brief: Brief) -> None:
    contributions = _clean_contributions(vi_brief)
    contributions["arranger"]["energy_per_section"]["chorus_final"] = 7
    contributions["arranger"]["energy_per_section"]["chorus_1"] = 7
    contributions["arranger"]["per_section_textures"] = {
        "chorus": "same texture",
        "chorus_final": "same texture",
    }
    contributions["composer"]["peak_section"] = "bridge"
    issues = check_compliance(vi_brief, contributions)
    codes = {i.code for i in issues if i.persona_role == "arranger"}
    assert "final_chorus_flat" in codes or "final_chorus_same_energy" in codes


def test_arranger_final_chorus_distinct_via_composer_peak(vi_brief: Brief) -> None:
    """When Composer signals peak at chorus_final, equal energy is acceptable."""
    contributions = _clean_contributions(vi_brief)
    contributions["arranger"]["energy_per_section"]["chorus_final"] = 7
    contributions["arranger"]["energy_per_section"]["chorus_1"] = 7
    contributions["composer"]["peak_section"] = "chorus_final"
    issues = check_compliance(vi_brief, contributions)
    codes = {i.code for i in issues if i.persona_role == "arranger"}
    assert "final_chorus_flat" not in codes
    assert "final_chorus_same_energy" not in codes


def test_producer_suno_style_too_long_flagged(vi_brief: Brief) -> None:
    contributions = _clean_contributions(vi_brief)
    contributions["producer"]["suno_style_string"] = (
        "v-pop ballad, " * 30
    )
    issues = check_compliance(vi_brief, contributions)
    assert any(i.code == "suno_style_too_long" for i in issues)


def test_producer_vn_references_flagged(vi_brief: Brief) -> None:
    contributions = _clean_contributions(vi_brief)
    contributions["producer"]["references"] = [
        "Adele — Someone Like You",
        "Sam Smith — Stay With Me",
    ]
    issues = check_compliance(vi_brief, contributions)
    assert any(i.code == "references_not_vietnamese" for i in issues)


def test_producer_vn_references_not_required_for_english(en_brief: Brief) -> None:
    contributions = _clean_contributions(en_brief)
    contributions["producer"]["references"] = [
        "Adele — Someone Like You",
        "Sam Smith — Stay With Me",
    ]
    issues = check_compliance(en_brief, contributions)
    assert not any(i.code == "references_not_vietnamese" for i in issues)


def test_issues_by_persona_groups_correctly() -> None:
    issues = [
        ComplianceIssue("theorist", "a", "msg", "fix"),
        ComplianceIssue("composer", "b", "msg", "fix"),
        ComplianceIssue("theorist", "c", "msg", "fix"),
    ]
    grouped = issues_by_persona(issues)
    assert list(grouped.keys()) == ["theorist", "composer"]
    assert len(grouped["theorist"]) == 2
    assert grouped["theorist"][0].code == "a"
    assert grouped["theorist"][1].code == "c"


def test_format_issues_for_retry_renders_codes_and_fixes() -> None:
    issues = [
        ComplianceIssue("composer", "peak_in_verse_1", "verse_1 peak", "move it"),
    ]
    nudge = format_issues_for_retry(issues)
    assert "peak_in_verse_1" in nudge
    assert "move it" in nudge
    assert "COMPLIANCE" in nudge


def test_format_issues_for_retry_empty() -> None:
    assert format_issues_for_retry([]) == ""


def test_plan_refinement_clean_keeps_default(vi_brief: Brief) -> None:
    targets, by_role = _plan_refinement(vi_brief, _clean_contributions(vi_brief))
    assert targets == ["composer", "lyricist"]
    assert by_role == {}


def test_plan_refinement_adds_persona_with_issues(vi_brief: Brief) -> None:
    contributions = _clean_contributions(vi_brief)
    contributions["theorist"]["chord_progression_per_section"]["verse"] = ["Em"]
    contributions["producer"]["suno_style_string"] = "x," * 200
    targets, by_role = _plan_refinement(vi_brief, contributions)
    assert "theorist" in targets
    assert "producer" in targets
    # Composer + Lyricist still in targets (default set).
    assert "composer" in targets
    assert "lyricist" in targets
    # Order respects council seniority.
    assert targets.index("theorist") < targets.index("composer")
    assert targets.index("composer") < targets.index("lyricist")
    assert targets.index("lyricist") < targets.index("producer")
    assert "theorist" in by_role
    assert "producer" in by_role


def test_plan_refinement_never_includes_critic(vi_brief: Brief) -> None:
    targets, _ = _plan_refinement(vi_brief, _clean_contributions(vi_brief))
    assert "critic" not in targets
