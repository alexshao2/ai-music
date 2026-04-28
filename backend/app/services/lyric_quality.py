"""Programmatic quality checks for Lyricist output.

Even with a strict system prompt, models routinely slip placeholders
(``[chờ Lyricist]``, ``[Hook — …]``, ``<full lyric block>``) or copy the
schema instructions verbatim. Catching these in Python lets us retry the
Lyricist with a pointed nudge rather than relying on the A&R Critic to
flag them (Critic feedback only triggers the refine pass, by which point
the draft is already half-baked).

We keep the rules conservative — we only flag issues a *reasonable human
reviewer* would also flag (empty section, brackets-around-metadata, schema
placeholder text). Stylistic complaints ("too clichéd") belong to the
Critic, not here.
"""
from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

# Expected section keys. A Lyricist output missing any of these is
# incomplete. We don't require ``verse_2`` because some forms (intro-
# chorus-only hooks) legitimately omit it.
_REQUIRED_SECTIONS: tuple[str, ...] = ("verse_1", "pre_chorus", "chorus", "bridge")

# Minimum characters per section. Below this, the block is either empty
# or a one-line stub.
_MIN_SECTION_CHARS = 30

# Patterns that indicate the model returned a placeholder / schema hint
# instead of real lyrics. Matches are case-insensitive.
_PLACEHOLDER_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\[\s*ch[ờo]\s+(lyricist|tinh ch[ỉi]nh|hook|ch[ưu]a)", re.IGNORECASE),
    re.compile(r"\[\s*hook\s*[—\-–]", re.IGNORECASE),
    re.compile(r"\[\s*verse\s*\d?\s*[—\-–]\s*", re.IGNORECASE),
    re.compile(r"<\s*full\s+lyric\s+block", re.IGNORECASE),
    re.compile(r"<\s*\.\.\.\s*>"),
    re.compile(r"\bplaceholder\b", re.IGNORECASE),
    re.compile(r"\bTO\s*DO\b", re.IGNORECASE),
    re.compile(r"lorem\s+ipsum", re.IGNORECASE),
    # Model sometimes echoes the schema's <...> markers.
    re.compile(r"<concrete\s+VN\s+detail", re.IGNORECASE),
    re.compile(r"<same\s+lyrics\s+with", re.IGNORECASE),
)

# Very rough VN-diacritic detector — true V-pop lyrics will have dozens of
# these. English output for a VN brief is a regression worth flagging.
_VN_DIACRITIC_RE = re.compile(
    r"[àáâãèéêìíòóôõùúăđĩũơưạảấầẩẫậắằẳẵặẹẻẽềếểễệỉịọỏốồổỗộớờởỡợụủứừửữựỳỵỷỹ]",
    re.IGNORECASE,
)

# Short common-stop-word heuristic: if a "lyric" is >=90% single-word
# English tokens for a VN brief, it's probably the model writing in the
# wrong language.
_ENGLISH_FILLER_THRESHOLD = 0.6


@dataclass(frozen=True)
class LyricIssue:
    """One concrete problem found in lyric output."""

    section: str
    """Section key (``verse_1``, ``chorus``, ...) or ``""`` for global."""

    code: str
    """Stable slug for programmatic tests (e.g. ``placeholder``)."""

    message: str
    """Human-readable fix hint, phrased as an imperative."""


def _placeholder_hits(text: str) -> list[str]:
    return [pat.pattern for pat in _PLACEHOLDER_PATTERNS if pat.search(text)]


def _vn_ratio(text: str) -> float:
    """Rough share of VN-diacritic-bearing chars. 0 for pure ASCII."""
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return 0.0
    vn = sum(1 for c in letters if _VN_DIACRITIC_RE.match(c))
    return vn / len(letters)


def validate_lyrics(
    contributions: Mapping[str, Any],
    *,
    language: str,
) -> list[LyricIssue]:
    """Return a list of issues a retry prompt should ask Lyricist to fix.

    ``contributions`` is the ``contributions`` sub-object from Lyricist's
    JSON response (the one containing ``lyrics``, ``hook_line``, ...).
    ``language`` is ``brief.language`` (``vi`` / ``en`` / ``ja`` / ``ko``).
    Empty list means the output looks acceptable.
    """
    issues: list[LyricIssue] = []

    lyrics = contributions.get("lyrics") if isinstance(contributions, Mapping) else None
    if not isinstance(lyrics, Mapping) or not lyrics:
        issues.append(
            LyricIssue(
                section="",
                code="missing_lyrics",
                message="Thiếu object 'lyrics'. Cần lời thật cho từng section.",
            )
        )
        return issues

    for section in _REQUIRED_SECTIONS:
        raw = lyrics.get(section)
        if not isinstance(raw, str) or not raw.strip():
            issues.append(
                LyricIssue(
                    section=section,
                    code="empty_section",
                    message=(
                        f"Section '{section}' đang trống. Viết lời THẬT, "
                        f"đủ dòng theo syllables_per_phrase của Composer."
                    ),
                )
            )
            continue

        text = raw.strip()
        if len(text) < _MIN_SECTION_CHARS:
            issues.append(
                LyricIssue(
                    section=section,
                    code="too_short",
                    message=(
                        f"Section '{section}' quá ngắn ({len(text)} ký tự). "
                        f"Viết đủ dòng, mỗi dòng đếm đúng syllable."
                    ),
                )
            )

        hits = _placeholder_hits(text)
        if hits:
            issues.append(
                LyricIssue(
                    section=section,
                    code="placeholder",
                    message=(
                        f"Section '{section}' chứa placeholder/schema hint "
                        f"({', '.join(hits[:2])}). Thay bằng câu thật."
                    ),
                )
            )

        if language.lower() == "vi" and _vn_ratio(text) < 0.02:
            issues.append(
                LyricIssue(
                    section=section,
                    code="wrong_language",
                    message=(
                        f"Section '{section}' không có dấu tiếng Việt — "
                        f"brief yêu cầu language='vi'. Viết lại bằng tiếng Việt có dấu."
                    ),
                )
            )

    # Hook line
    hook = contributions.get("hook_line") if isinstance(contributions, Mapping) else None
    if isinstance(hook, str):
        hook_stripped = hook.strip()
        if not hook_stripped or _placeholder_hits(hook_stripped):
            issues.append(
                LyricIssue(
                    section="hook_line",
                    code="placeholder_hook",
                    message="'hook_line' trống hoặc là placeholder. Đưa câu hook thật.",
                )
            )

    return issues


def format_issues_for_retry(issues: list[LyricIssue]) -> str:
    """Render validator output as a prompt nudge for the next retry.

    The nudge is appended to Lyricist's user prompt as a "Your previous
    output had these problems — fix each one" block. Kept short so it
    doesn't blow the token budget.
    """
    if not issues:
        return ""
    lines = [
        "## LẦN TRƯỚC BỊ CHÁM LỖI — LẦN NÀY PHẢI SỬA",
        "Bản LLM vừa trả về có các vấn đề sau. Viết lại bản MỚI, đảm bảo:",
    ]
    for issue in issues:
        prefix = f"[{issue.section}] " if issue.section else ""
        lines.append(f"- {prefix}{issue.message}")
    lines.append(
        "QUAN TRỌNG: Trả về JSON hoàn chỉnh với lời THẬT cho mọi section. "
        "Không được sao chép schema template (<...>, [chờ...], [Hook —...])."
    )
    return "\n".join(lines)


__all__ = [
    "LyricIssue",
    "validate_lyrics",
    "format_issues_for_retry",
]
