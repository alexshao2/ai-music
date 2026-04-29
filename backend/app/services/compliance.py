"""Deterministic compliance checks on council persona contributions.

The Critic prompt asks the LLM to verify ~10 compliance booleans
(``bar_duration_math_ok``, ``hook_recipe_specified``,
``suno_style_string_within_200`` …). In practice the Critic LLM happily
returns ``true`` for every one of them even when the math is clearly off,
so we re-implement the checks in Python.

Each check is **deterministic, knowledge-driven, and cheap** (regex / set
membership / arithmetic). They run on the structured ``contributions``
dict produced by each persona — same shape the council already builds —
and return a list of :class:`ComplianceIssue` records tagged with the
*owning persona*. The council can then route each persona's issues into a
targeted refinement turn instead of rerunning the whole hội đồng.

Lyric-level checks (Vietnamese tone-at-peak, syllable count vs Composer
spec) belong in :mod:`app.services.lyric_quality` and are intentionally
not duplicated here.
"""
from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from app.schemas import Brief

# ---------- Constants ----------

# 8 hook recipes the Composer prompt forces. The persona may add their own
# qualifier (case, punctuation), so we match by a normalised token.
_HOOK_RECIPES: tuple[str, ...] = (
    "recipe-1-repeat-jump",
    "recipe-2-step-down-rest",
    "recipe-3-arpeggio-up",
    "recipe-4-rhythm-shift",
    "recipe-5-question-answer",
    "recipe-6-pedal-chord-shift",
    "recipe-7-octave-leap",
    "recipe-8-whole-tone",
)
_HOOK_RECIPE_KEYS: frozenset[str] = frozenset(
    r.replace("-", "").replace("_", "").lower() for r in _HOOK_RECIPES
)

# Sections where placing the peak note breaks the dynamic arc (Composer
# prompt rule: peak must sit in chorus or bridge, never verse_1).
_FORBIDDEN_PEAK_SECTIONS: frozenset[str] = frozenset(
    {"verse", "verse_1", "verse 1", "intro"}
)

# Suno Style field hard cap — Suno truncates at 200 chars in Custom mode.
_SUNO_STYLE_HARD_CAP = 200

# Bar-duration math tolerance. Theorist + Composer prompts both quote
# ±15%; we use ±20% here to avoid flagging legitimate intentional padding
# (count-in bars, fade tails) — checks should be high-precision when they
# fire so the persona retries on real problems only.
_BAR_DURATION_TOLERANCE = 0.20

# Minimum concrete chords required per section before we consider the
# progression "concrete" (Theorist prompt asks for ≥4 cụ thể).
_MIN_CHORDS_PER_SECTION = 3

# Roman-numeral-only chord shorthand. Theorist must give concrete chords
# with quality (Em7, F#maj7) — never "i", "V", "iv". A single-or-double
# letter Roman numeral with optional flat / sharp prefix is the sentinel.
_ROMAN_NUMERAL_RE = re.compile(
    r"^[♭♯b#]?(IV|VII|III|II|VI|V|I|iv|vii|iii|ii|vi|v|i)\d*(\s*[°ø+\-])?$"
)

# Strip-down threshold for Arranger.energy_per_section. The dynamic-arc
# templates (T1/T2/T3) all include at least one section ≤ 4 of 9.
_STRIP_DOWN_MAX_ENERGY = 4

# Vietnamese pop / V-pop artist tokens that act as a positive signal in
# Producer.references when brief.language=='vi'. The list is intentionally
# short — common, unambiguous artists. Missing a name here is fine; the
# check is "at least one VN artist appears", not "every artist is VN".
_VN_ARTIST_TOKENS: frozenset[str] = frozenset(
    {
        "hà anh tuấn",
        "ha anh tuan",
        "vũ.",
        "vu.",
        "vũ",
        "trịnh công sơn",
        "trinh cong son",
        "phú quang",
        "phu quang",
        "khắc hưng",
        "khac hung",
        "hứa kim tuyền",
        "hua kim tuyen",
        "đen",
        "đen vâu",
        "den vau",
        "sơn tùng",
        "son tung",
        "mỹ tâm",
        "my tam",
        "lệ quyên",
        "le quyen",
        "trúc nhân",
        "truc nhan",
        "vũ cát tường",
        "vu cat tuong",
        "noo phước thịnh",
        "tóc tiên",
        "đông nhi",
        "bích phương",
        "bich phuong",
        "min",
        "amee",
        "erik",
        "đức phúc",
        "duc phuc",
        "hoàng dũng",
        "hoang dung",
        "phan mạnh quỳnh",
        "phan manh quynh",
        "anh trai",
        "ngọt",
        "ngot",
        "chillies",
        "trang",
        "vũ thanh vân",
        "tlinh",
        "mck",
        "ricky star",
        "low g",
        "rhymastic",
        "wowy",
        "binz",
    }
)


@dataclass(frozen=True)
class ComplianceIssue:
    """One concrete deterministic problem found in council contributions."""

    persona_role: str
    """``theorist`` / ``composer`` / ``arranger`` / ``producer``."""

    code: str
    """Stable slug for programmatic tests + telemetry."""

    message: str
    """Human-readable problem statement (Vietnamese, terse)."""

    fix_hint: str
    """Imperative fix suggestion appended to the persona's retry prompt."""


# ---------- Theorist checks ----------


def _theorist_bar_duration_math(
    brief: Brief, theorist: Mapping[str, Any]
) -> ComplianceIssue | None:
    """``bar_count_total × 240 / tempo_bpm`` should hit ``brief.duration_sec`` ±20%.

    The 240 constant is correct for 4/4 — 4 beats × 60s/min. We approximate
    other time signatures by reading ``time_signature`` and adjusting the
    beats-per-bar factor; default to 4 when the persona didn't specify.
    """
    bar_count = theorist.get("bar_count_total")
    tempo = theorist.get("tempo_bpm")
    if not isinstance(bar_count, (int, float)) or bar_count <= 0:
        return None
    if not isinstance(tempo, (int, float)) or tempo <= 0:
        return None

    beats_per_bar = 4
    ts = str(theorist.get("time_signature") or "").strip()
    m = re.match(r"^\s*(\d+)\s*/\s*(\d+)\s*$", ts)
    if m:
        num = int(m.group(1))
        beats_per_bar = num if num > 0 else 4

    duration_sec = bar_count * beats_per_bar * 60.0 / tempo
    target = float(brief.duration_sec)
    if target <= 0:
        return None
    delta = abs(duration_sec - target) / target
    if delta <= _BAR_DURATION_TOLERANCE:
        return None
    return ComplianceIssue(
        persona_role="theorist",
        code="bar_duration_math",
        message=(
            f"bar_count_total={int(bar_count)} ở {int(tempo)} BPM ({ts or '4/4'}) "
            f"ra ~{duration_sec:.0f}s — lệch {delta*100:.0f}% so với "
            f"brief.duration_sec={brief.duration_sec}s (giới hạn ±20%)."
        ),
        fix_hint=(
            f"Điều chỉnh bar_count_total hoặc section_bars để bar × beats × 60 / tempo "
            f"≈ {brief.duration_sec}s. Vd: ở {int(tempo)} BPM cần "
            f"~{int(target * tempo / (60 * beats_per_bar))} bar."
        ),
    )


def _theorist_chord_progression_concrete(
    theorist: Mapping[str, Any],
) -> list[ComplianceIssue]:
    """Each section's chord list must have ≥3 entries with concrete chord quality.

    Roman numerals like ``I``, ``V``, ``iv`` are flagged because the prompt
    requires concrete chords (``Em7``, not ``i``). We only mark sections
    that are present in the contribution — missing sections are caught by
    the bar-math check or by Arranger consistency.
    """
    progressions = theorist.get("chord_progression_per_section")
    if not isinstance(progressions, Mapping):
        return []
    issues: list[ComplianceIssue] = []
    for section, chords in progressions.items():
        if not isinstance(chords, list):
            continue
        chord_strs = [str(c).strip() for c in chords if str(c).strip()]
        if len(chord_strs) < _MIN_CHORDS_PER_SECTION:
            issues.append(
                ComplianceIssue(
                    persona_role="theorist",
                    code="chord_progression_too_short",
                    message=(
                        f"Section '{section}' chỉ có {len(chord_strs)} chord — "
                        f"cần ≥{_MIN_CHORDS_PER_SECTION} chord cụ thể."
                    ),
                    fix_hint=(
                        f"Đưa thêm hợp âm cho '{section}' (ít nhất "
                        f"{_MIN_CHORDS_PER_SECTION}); mỗi chord có chất "
                        f"(Em7, không phải Em một mình)."
                    ),
                )
            )
            continue
        roman_only = [c for c in chord_strs if _ROMAN_NUMERAL_RE.match(c)]
        if roman_only:
            issues.append(
                ComplianceIssue(
                    persona_role="theorist",
                    code="chord_roman_numeral",
                    message=(
                        f"Section '{section}' dùng Roman numeral "
                        f"({', '.join(roman_only[:3])}). Cần chord cụ thể với root note."
                    ),
                    fix_hint=(
                        f"Thay {', '.join(roman_only[:3])} ở '{section}' bằng "
                        f"hợp âm cụ thể trong key đã chọn (vd 'Em7' thay 'i7')."
                    ),
                )
            )
    return issues


def _theorist_key_concrete(theorist: Mapping[str, Any]) -> ComplianceIssue | None:
    """``key`` must be a concrete root + quality (e.g. ``E minor``)."""
    key = str(theorist.get("key") or "").strip()
    if not key:
        return None
    # "minor" / "major" alone — no root note.
    if re.match(r"^(major|minor)$", key, re.IGNORECASE):
        return ComplianceIssue(
            persona_role="theorist",
            code="key_missing_root",
            message=f"key='{key}' thiếu root note (cần 'E minor' chứ không phải 'minor').",
            fix_hint="Đặt key cụ thể với root note + quality, vd 'E minor' / 'F# major'.",
        )
    return None


# ---------- Composer checks ----------


def _composer_section_bars_math(
    brief: Brief, theorist: Mapping[str, Any], composer: Mapping[str, Any]
) -> ComplianceIssue | None:
    """``sum(section_bars) × beats × 60 / tempo`` must hit ``duration_sec`` ±20%.

    Independent of the Theorist's ``bar_count_total`` because Composer often
    overrides it via per-section bar counts.
    """
    section_bars = composer.get("section_bars")
    if not isinstance(section_bars, Mapping) or not section_bars:
        return None
    song_form = composer.get("song_form")
    tempo = theorist.get("tempo_bpm")
    if not isinstance(tempo, (int, float)) or tempo <= 0:
        return None

    beats_per_bar = 4
    ts = str(theorist.get("time_signature") or "").strip()
    m = re.match(r"^\s*(\d+)\s*/\s*(\d+)\s*$", ts)
    if m:
        num = int(m.group(1))
        beats_per_bar = num if num > 0 else 4

    if isinstance(song_form, list) and song_form:
        # Sum bars by walking the form so verse-chorus repeats are counted.
        total_bars = 0
        for sec in song_form:
            sec_key = str(sec).strip()
            v = section_bars.get(sec_key) or section_bars.get(sec_key.split("_")[0])
            if isinstance(v, (int, float)) and v > 0:
                total_bars += int(v)
        if total_bars == 0:
            return None
    else:
        total_bars = sum(
            int(v) for v in section_bars.values() if isinstance(v, (int, float)) and v > 0
        )
        if total_bars == 0:
            return None

    duration_sec = total_bars * beats_per_bar * 60.0 / tempo
    target = float(brief.duration_sec)
    delta = abs(duration_sec - target) / target
    if delta <= _BAR_DURATION_TOLERANCE:
        return None
    return ComplianceIssue(
        persona_role="composer",
        code="section_bars_math",
        message=(
            f"Tổng section_bars={total_bars} ở {int(tempo)} BPM ra ~{duration_sec:.0f}s "
            f"— lệch {delta*100:.0f}% so với brief.duration_sec={brief.duration_sec}s."
        ),
        fix_hint=(
            f"Điều chỉnh section_bars / song_form để tổng bar × beats × 60 / tempo "
            f"≈ {brief.duration_sec}s."
        ),
    )


def _composer_peak_section(composer: Mapping[str, Any]) -> ComplianceIssue | None:
    """``peak_section`` must NOT be ``verse_1`` / ``intro`` (breaks dynamic arc)."""
    peak = str(composer.get("peak_section") or "").strip().lower()
    if not peak:
        return None
    if peak in _FORBIDDEN_PEAK_SECTIONS:
        return ComplianceIssue(
            persona_role="composer",
            code="peak_in_verse_1",
            message=f"peak_section='{peak}' phá dynamic arc (đỉnh phải ở chorus / bridge).",
            fix_hint=(
                "Chuyển peak_note sang chorus_final hoặc bridge climax; "
                "verse_1 phải mở ở vùng giữa range, để dành note cao cho hook."
            ),
        )
    return None


def _composer_hook_recipe(composer: Mapping[str, Any]) -> ComplianceIssue | None:
    """``hook_recipe_used`` must be one of the 8 recipes."""
    recipe = str(composer.get("hook_recipe_used") or "").strip()
    if not recipe:
        return ComplianceIssue(
            persona_role="composer",
            code="hook_recipe_missing",
            message="Thiếu hook_recipe_used — phải chọn 1 trong 8 recipe.",
            fix_hint=(
                "Đặt hook_recipe_used = 1 trong: "
                + ", ".join(_HOOK_RECIPES)
                + "."
            ),
        )
    norm = re.sub(r"[\s_\-]", "", recipe).lower()
    if norm not in _HOOK_RECIPE_KEYS:
        return ComplianceIssue(
            persona_role="composer",
            code="hook_recipe_unknown",
            message=f"hook_recipe_used='{recipe}' không thuộc 8 recipe đã định danh.",
            fix_hint=(
                "Chọn lại 1 trong: " + ", ".join(_HOOK_RECIPES) + "."
            ),
        )
    return None


# ---------- Arranger checks ----------


def _arranger_strip_down(arranger: Mapping[str, Any]) -> ComplianceIssue | None:
    """``energy_per_section`` must contain at least one value ≤ 4 of 9."""
    energy = arranger.get("energy_per_section")
    if not isinstance(energy, Mapping) or not energy:
        return None
    numeric = [
        (str(k), float(v))
        for k, v in energy.items()
        if isinstance(v, (int, float))
    ]
    if not numeric:
        return None
    if any(v <= _STRIP_DOWN_MAX_ENERGY for _, v in numeric):
        return None
    lo_section, lo_value = min(numeric, key=lambda kv: kv[1])
    return ComplianceIssue(
        persona_role="arranger",
        code="no_strip_down",
        message=(
            f"energy_per_section không có section nào ≤ {_STRIP_DOWN_MAX_ENERGY} "
            f"(min='{lo_section}'={lo_value:g}) — bài thiếu strip-down, "
            f"dynamic arc sẽ phẳng."
        ),
        fix_hint=(
            "Hạ energy của 1 section (thường intro hoặc bridge) xuống ≤ 4 — "
            "vd intro=2, bridge=3 — để có chỗ build-up vào chorus."
        ),
    )


def _arranger_final_chorus_distinct(
    arranger: Mapping[str, Any], composer: Mapping[str, Any]
) -> ComplianceIssue | None:
    """``chorus_final`` must differ from ``chorus_1`` in energy or texture.

    A common AI music defect is a flat repetition of the chorus three times
    with identical energy / instrumentation. We compare on:
      - energy_per_section[chorus_final] vs energy_per_section[chorus_1]
      - per_section_textures[chorus_final] vs per_section_textures[chorus]

    The check fires only when both values exist; missing fields are handled
    by other checks.
    """
    energy = arranger.get("energy_per_section")
    textures = arranger.get("per_section_textures")
    if not isinstance(energy, Mapping):
        return None

    e_first = energy.get("chorus_1") or energy.get("chorus")
    e_final = energy.get("chorus_final") or energy.get("chorus_3")
    if e_first is None or e_final is None:
        return None
    try:
        e_first_v = float(e_first)
        e_final_v = float(e_final)
    except (TypeError, ValueError):
        return None

    energy_distinct = abs(e_final_v - e_first_v) >= 1.0

    texture_distinct = True
    if isinstance(textures, Mapping):
        t_first = str(textures.get("chorus") or textures.get("chorus_1") or "").strip()
        t_final = str(textures.get("chorus_final") or textures.get("chorus_3") or "").strip()
        if t_first and t_final and t_first == t_final:
            texture_distinct = False

    # Composer often signals modulation by a higher peak in the final chorus.
    # When peak_section is chorus_final, accept it as a distinguishing mark.
    composer_peak = str(composer.get("peak_section") or "").strip().lower()
    composer_signals_final = composer_peak in {"chorus_final", "final_chorus", "chorus_3"}

    if energy_distinct or composer_signals_final:
        return None
    if not texture_distinct:
        return ComplianceIssue(
            persona_role="arranger",
            code="final_chorus_flat",
            message=(
                "chorus_final có cùng energy + texture với chorus_1 — "
                "thiếu lift cuối bài (modulate / counter-melody / extra layer)."
            ),
            fix_hint=(
                "Tăng energy_per_section.chorus_final ≥ +1 so với chorus_1, "
                "hoặc đổi per_section_textures.chorus_final (thêm vocal stack, "
                "string layer, modulation +1 semitone)."
            ),
        )
    if not energy_distinct:
        return ComplianceIssue(
            persona_role="arranger",
            code="final_chorus_same_energy",
            message=(
                f"energy chorus_final={e_final_v:g} == chorus_1={e_first_v:g} — "
                f"final chorus phải có lift dynamic."
            ),
            fix_hint=(
                "Tăng energy_per_section.chorus_final ≥ +1 so với chorus_1."
            ),
        )
    return None


# ---------- Producer checks ----------


def _producer_suno_style_length(
    producer: Mapping[str, Any],
) -> ComplianceIssue | None:
    """``suno_style_string`` must be ≤ 200 chars (Suno truncation)."""
    style = str(producer.get("suno_style_string") or "").strip()
    if not style:
        return None
    if len(style) <= _SUNO_STYLE_HARD_CAP:
        return None
    return ComplianceIssue(
        persona_role="producer",
        code="suno_style_too_long",
        message=(
            f"suno_style_string dài {len(style)} ký tự — Suno cắt ở "
            f"{_SUNO_STYLE_HARD_CAP}, mất phần đuôi."
        ),
        fix_hint=(
            f"Rút ngắn suno_style_string xuống ≤ {_SUNO_STYLE_HARD_CAP} ký tự "
            f"(aim 140-180); ưu tiên giữ genre, tempo, key, instruments, vocal."
        ),
    )


def _producer_vn_references(
    brief: Brief, producer: Mapping[str, Any]
) -> ComplianceIssue | None:
    """When ``brief.language=='vi'``, ≥ 1 reference must be a VN artist."""
    if brief.language.lower() != "vi":
        return None
    refs = producer.get("references")
    if not isinstance(refs, list) or not refs:
        return None
    haystack = " | ".join(str(r) for r in refs).lower()
    if any(token in haystack for token in _VN_ARTIST_TOKENS):
        return None
    return ComplianceIssue(
        persona_role="producer",
        code="references_not_vietnamese",
        message=(
            "brief.language='vi' nhưng references không có artist Việt — "
            "tham chiếu Tây cho V-pop sẽ kéo Suno style sai."
        ),
        fix_hint=(
            "Thêm ≥1 V-pop reference (vd Hà Anh Tuấn — Tháng Tư, Vũ. — Lạ Lùng, "
            "Phan Mạnh Quỳnh — Có Chàng Trai Viết Lên Cây)."
        ),
    )


# ---------- Public API ----------


def check_compliance(
    brief: Brief, contributions: Mapping[str, Mapping[str, Any]]
) -> list[ComplianceIssue]:
    """Run every deterministic check on the council's contributions.

    Lyric-level checks are NOT included — those live in
    :mod:`app.services.lyric_quality` and are run inside the Lyricist
    retry loop. Returns an empty list when the council output is
    compliance-clean.
    """
    issues: list[ComplianceIssue] = []
    theorist = contributions.get("theorist") or {}
    composer = contributions.get("composer") or {}
    arranger = contributions.get("arranger") or {}
    producer = contributions.get("producer") or {}

    if (i := _theorist_key_concrete(theorist)) is not None:
        issues.append(i)
    if (i := _theorist_bar_duration_math(brief, theorist)) is not None:
        issues.append(i)
    issues.extend(_theorist_chord_progression_concrete(theorist))

    if (i := _composer_section_bars_math(brief, theorist, composer)) is not None:
        issues.append(i)
    if (i := _composer_peak_section(composer)) is not None:
        issues.append(i)
    if (i := _composer_hook_recipe(composer)) is not None:
        issues.append(i)

    if (i := _arranger_strip_down(arranger)) is not None:
        issues.append(i)
    if (i := _arranger_final_chorus_distinct(arranger, composer)) is not None:
        issues.append(i)

    if (i := _producer_suno_style_length(producer)) is not None:
        issues.append(i)
    if (i := _producer_vn_references(brief, producer)) is not None:
        issues.append(i)

    return issues


def issues_by_persona(
    issues: list[ComplianceIssue],
) -> dict[str, list[ComplianceIssue]]:
    """Group issues by ``persona_role`` preserving discovery order."""
    out: dict[str, list[ComplianceIssue]] = {}
    for issue in issues:
        out.setdefault(issue.persona_role, []).append(issue)
    return out


def format_issues_for_retry(issues: list[ComplianceIssue]) -> str:
    """Render persona-scoped issues as a nudge for the refinement prompt.

    Mirrors :func:`app.services.lyric_quality.format_issues_for_retry` so the
    LLM sees a consistent "you got these things wrong, fix them" block
    regardless of which validator caught them.
    """
    if not issues:
        return ""
    lines = [
        "## COMPLIANCE CHECK FAIL — LẦN NÀY PHẢI SỬA",
        "Bản LLM vừa ra fail các kiểm tra deterministic sau. Trả về contributions "
        "MỚI giải quyết tất cả:",
    ]
    for issue in issues:
        lines.append(f"- [{issue.code}] {issue.message}")
        lines.append(f"  → Fix: {issue.fix_hint}")
    lines.append(
        "QUAN TRỌNG: Trả về JSON đúng schema, KHÔNG bỏ field — chỉ sửa giá trị "
        "cần sửa và giữ nguyên phần đã đạt."
    )
    return "\n".join(lines)


__all__ = [
    "ComplianceIssue",
    "check_compliance",
    "issues_by_persona",
    "format_issues_for_retry",
]
