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

import logging
import re
import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

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

# V-pop clichés are loaded from ``knowledge/lyrics/cliche-bank-vn.md`` so
# the Critic prompt, the Lyricist retry nudge, and this validator stay in
# sync. The hardcoded fallback below is only used when the knowledge file
# is missing (rare — the file ships with the repo) or unparseable.
_CLICHE_FALLBACK: tuple[str, ...] = (
    "trái tim tan vỡ",
    "nỗi đau câm lặng",
    "lạc lõng giữa đám đông",
    "bóng hình em",
    "yêu em đến mãi",
    "lá vàng rơi",
    "lệ rơi trên má",
    "mẹ già ngồi đợi",
    "nhớ em da diết",
    "trăng khuya",
    "em phụ tình anh",
    "đàn bà bạc tình",
)


def _cliche_bank_path() -> Path:
    """Resolve the cliché bank markdown path relative to this file."""
    return (
        Path(__file__).resolve().parent.parent.parent.parent
        / "knowledge"
        / "lyrics"
        / "cliche-bank-vn.md"
    )


def _parse_cliche_bank(md_text: str) -> list[str]:
    """Extract cliché phrases from the markdown table column 1.

    The bank uses standard markdown tables:

        | Cliché          | Lý do tránh         | Thay bằng |
        |--               |--                   |--         |
        | "Trái tim tan vỡ" | Quá phổ biến      | "..."     |

    We collect cells from the first column of every data row (rows that
    are not the header or separator), strip surrounding quotes/whitespace,
    drop placeholders, and lowercase for case-insensitive matching.

    Multi-line free text outside tables is ignored — the file's "Phrasing
    cliché" section uses table rows with a constructed phrase in column 1
    (e.g. ``"Anh yêu em ___ / Mà em không hiểu"``); these contain
    underscores / slashes that don't survive as a useful regex match, so
    we filter them out.
    """
    seen: set[str] = set()
    out: list[str] = []
    for raw_line in md_text.splitlines():
        line = raw_line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if not cells:
            continue
        first = cells[0]
        # Skip header rows ("Cliché", "Cliché Gen Z", ...) and separator
        # rows ("--", ":---:").
        if not first or set(first) <= set("-: "):
            continue
        if first.lower().startswith(("cliché", "cấu trúc", "phrase")):
            continue
        # Drop wrapping quotes (bank uses both straight and curly quotes).
        phrase = first.strip("\"\u201c\u201d'`")
        # Skip "phrasing cliché" rows that contain templating
        # placeholders we can't usefully regex-match, or rows whose
        # first column also embeds parenthesised meta ("Mưa rơi"
        # (mùa buồn)) which leaks an unbalanced quote/paren after
        # outer-quote stripping.
        if any(ch in phrase for ch in ("___", "...", "/", '"', "(", ")")):
            continue
        phrase = phrase.lower().strip()
        if not phrase or len(phrase) < 6:
            continue
        if phrase in seen:
            continue
        seen.add(phrase)
        out.append(phrase)
    return out


def _load_cliche_phrases() -> tuple[str, ...]:
    """Load + parse the cliché bank, falling back to the in-code list."""
    path = _cliche_bank_path()
    try:
        md_text = path.read_text(encoding="utf-8")
    except OSError as exc:
        log.warning(
            "Cliché bank not readable at %s (%s); using hardcoded fallback",
            path, exc,
        )
        return _CLICHE_FALLBACK
    parsed = _parse_cliche_bank(md_text)
    if len(parsed) < len(_CLICHE_FALLBACK):
        # Parse produced fewer entries than fallback — likely a parser
        # regression on a future file format change. Union the two so
        # we never *lose* coverage.
        merged: list[str] = list(parsed)
        seen = set(parsed)
        for p in _CLICHE_FALLBACK:
            if p not in seen:
                merged.append(p)
                seen.add(p)
        log.info(
            "Cliché bank parsed %d phrases; merged with %d fallback → %d total",
            len(parsed), len(_CLICHE_FALLBACK), len(merged),
        )
        return tuple(merged)
    return tuple(parsed)


_CLICHE_PHRASES: tuple[str, ...] = _load_cliche_phrases()
_CLICHE_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(rf"(?<![\wÀ-ỹ]){re.escape(p)}(?![\wÀ-ỹ])", re.IGNORECASE)
    for p in _CLICHE_PHRASES
)

# Generic Vietnamese nature/time tokens that, on their own, do not count
# as a "concrete imagery anchor" (per ``imagery-locales-vn.md`` rule 2).
# An ``imagery_locales_used`` array filled exclusively with these is
# basically empty.
_GENERIC_IMAGERY_TOKENS: frozenset[str] = frozenset(
    {
        "mùa",
        "đêm",
        "ngày",
        "trời",
        "gió",
        "nắng",
        "mưa",
        "sao",
        "mây",
        "biển",
        "sông",
        "núi",
        "thu",
        "xuân",
        "hè",
        "đông",
        "hoa",
        "lá",
        "mây trời",
        "bầu trời",
        "tình yêu",
    }
)

# Sections where verbatim line repetition is structurally expected
# (e.g. chorus hooks). Repetition outside these is usually a
# generation glitch.
_REPETITION_ALLOWED_SECTIONS: frozenset[str] = frozenset(
    {"chorus", "chorus_1", "chorus_2", "chorus_final", "hook"}
)
_MAX_LINE_REPEATS_NON_CHORUS = 2


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


def _cliche_hits(text: str) -> list[str]:
    """Return the surface form of any cliché phrases found in ``text``."""
    found: list[str] = []
    for phrase, pattern in zip(_CLICHE_PHRASES, _CLICHE_PATTERNS, strict=True):
        if pattern.search(text):
            found.append(phrase)
    return found


def _max_consecutive_line_repeats(text: str) -> tuple[int, str]:
    """Return ``(max_run, line)`` of the most-repeated consecutive line.

    Empty / whitespace-only lines are ignored. ``max_run == 1`` means
    no repetition at all.
    """
    raw_lines = [ln.strip() for ln in text.splitlines()]
    lines = [ln for ln in raw_lines if ln]
    if not lines:
        return 0, ""
    best_run = 1
    best_line = lines[0]
    current_run = 1
    for prev, curr in zip(lines, lines[1:], strict=False):
        if curr == prev:
            current_run += 1
            if current_run > best_run:
                best_run = current_run
                best_line = curr
        else:
            current_run = 1
    return best_run, best_line


def _vn_ratio(text: str) -> float:
    """Rough share of VN-diacritic-bearing chars. 0 for pure ASCII."""
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return 0.0
    vn = sum(1 for c in letters if _VN_DIACRITIC_RE.match(c))
    return vn / len(letters)


# --- Vietnamese tone classification ---------------------------------------
#
# A syllable's tone is encoded by Unicode combining marks in NFD form:
#   U+0300 (grave)        → huyền   (low falling)
#   U+0301 (acute)        → sắc      (high rising)
#   U+0303 (tilde)        → ngã      (broken/glottalised, ends rising)
#   U+0309 (hook above)   → hỏi      (dipping, low-mid)
#   U+0323 (dot below)    → nặng     (low + glottal stop)
#   (no combining mark)   → ngang    (level)
#
# At a melodic *peak* (the highest sustained note of the song, usually in
# the chorus / hook), tones that pull pitch DOWN make the syllable sound
# strained or wrong. Vietnamese songwriting tradition prefers ``ngang``,
# ``sắc``, ``ngã`` (or ``hỏi`` if executed well) on peak notes; ``huyền``
# and ``nặng`` are the cardinal sins of "tone-melody mismatch".

_TONE_GRAVE = "\u0300"      # huyền
_TONE_ACUTE = "\u0301"      # sắc
_TONE_TILDE = "\u0303"      # ngã
_TONE_HOOK = "\u0309"       # hỏi
_TONE_DOT_BELOW = "\u0323"  # nặng

# Tones we consider problematic when they land on a peak note.
_FALLING_TONES: frozenset[str] = frozenset({"huyền", "nặng"})

# Threshold: if more than this share of lines in ``peak_section`` end on a
# falling tone, the section is flagged. We don't fail on a single offender
# — VN lyric tradition allows occasional huyền/nặng at peak when used
# expressively — but a *majority* of falling endings is wrong.
_FALLING_TONE_THRESHOLD = 0.5

# Tolerance for syllables-per-line vs Composer's spec. Composer's
# ``syllables_per_phrase`` is approximate (it represents the melody's
# rhythmic shape, not a hard count); off-by-one is fine, off-by-three is
# not — the line won't fit the melody.
_SYLLABLE_TOLERANCE = 1


def _classify_vn_tone(syllable: str) -> str:
    """Return the tone name of a Vietnamese syllable (``ngang`` if none).

    Works on both NFC ("á") and NFD ("a" + U+0301) input by normalising
    to NFD first. Non-Vietnamese / non-letter input returns ``"ngang"``.
    """
    norm = unicodedata.normalize("NFD", syllable)
    if _TONE_GRAVE in norm:
        return "huyền"
    if _TONE_ACUTE in norm:
        return "sắc"
    if _TONE_TILDE in norm:
        return "ngã"
    if _TONE_HOOK in norm:
        return "hỏi"
    if _TONE_DOT_BELOW in norm:
        return "nặng"
    return "ngang"


# Vietnamese is monosyllabic — every space-separated word is exactly one
# syllable. Punctuation and the special markdown characters that bleed
# into LLM output are stripped before counting.
_SYLLABLE_TOKEN_RE = re.compile(r"[\wÀ-ỹ]+", re.UNICODE)


def _vn_syllables(line: str) -> list[str]:
    """Tokenise a Vietnamese line into syllable tokens."""
    return _SYLLABLE_TOKEN_RE.findall(line)


def _falling_tone_ratio(text: str) -> tuple[float, int, list[str]]:
    """Return ``(ratio, total_lines, sample_offenders)`` for a section.

    ``ratio`` is the share of non-empty lines whose *last* syllable carries
    a falling tone (huyền / nặng). ``sample_offenders`` is up to 3 raw
    lines we found, for the retry nudge. ``total_lines`` is 0 when the
    section text is empty / unsplittable.
    """
    raw_lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if not raw_lines:
        return 0.0, 0, []
    falling = 0
    offenders: list[str] = []
    for line in raw_lines:
        syllables = _vn_syllables(line)
        if not syllables:
            continue
        last_tone = _classify_vn_tone(syllables[-1])
        if last_tone in _FALLING_TONES:
            falling += 1
            if len(offenders) < 3:
                offenders.append(line)
    return falling / len(raw_lines), len(raw_lines), offenders


def _peak_section_from_composer(
    composer: Mapping[str, Any] | None,
) -> str | None:
    """Pick the most likely peak section name from Composer's contribution.

    Composer's contract emits ``peak_section`` (string) — but older drafts
    occasionally use ``peak`` or nest it under ``melodic_motifs``. We walk
    the obvious shapes and bail out gracefully when nothing usable exists.
    """
    if not isinstance(composer, Mapping):
        return None
    raw = composer.get("peak_section") or composer.get("peak")
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    return None


def _syllables_per_phrase_from_composer(
    composer: Mapping[str, Any] | None,
) -> dict[str, list[int]]:
    """Extract Composer's ``syllables_per_phrase`` as a section→counts map.

    Accepted shapes:

        {"verse": [8, 8, 9, 8], "chorus": [7, 7, 8, 8]}
        {"verse_1": 8, "chorus": [7, 7]}  # scalar collapses to single line

    Anything else is ignored. Missing key → empty map (caller skips check).
    """
    if not isinstance(composer, Mapping):
        return {}
    raw = composer.get("syllables_per_phrase")
    if not isinstance(raw, Mapping):
        return {}
    out: dict[str, list[int]] = {}
    for k, v in raw.items():
        if not isinstance(k, str) or not k:
            continue
        if isinstance(v, (int, float)):
            out[k] = [int(v)]
        elif isinstance(v, list):
            counts = [int(x) for x in v if isinstance(x, (int, float))]
            if counts:
                out[k] = counts
    return out


def _section_lyric_lines(text: str) -> list[str]:
    """Split a section's lyric block into non-empty lines."""
    return [ln.strip() for ln in text.splitlines() if ln.strip()]


def validate_lyrics(
    contributions: Mapping[str, Any],
    *,
    language: str,
    composer: Mapping[str, Any] | None = None,
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

        # Cliché audit: only meaningful for Vietnamese lyrics. The cliché
        # bank is curated for V-pop; English/JP/KR lyric have separate
        # cliché conventions that we don't model yet.
        if language.lower() == "vi":
            cliches = _cliche_hits(text)
            if cliches:
                issues.append(
                    LyricIssue(
                        section=section,
                        code="cliche_detected",
                        message=(
                            f"Section '{section}' chứa cliché V-pop "
                            f"({', '.join(cliches[:3])}). Thay bằng chi tiết quan "
                            f"sát được — xem cliche-bank-vn.md cột 'Thay bằng'."
                        ),
                    )
                )

        # Verbatim line repetition: chorus is allowed to repeat hooks,
        # but a verse with the same line >2 times in a row is almost
        # always a generation glitch.
        if section not in _REPETITION_ALLOWED_SECTIONS:
            run, repeated = _max_consecutive_line_repeats(text)
            if run > _MAX_LINE_REPEATS_NON_CHORUS:
                snippet = repeated[:40] + ("…" if len(repeated) > 40 else "")
                issues.append(
                    LyricIssue(
                        section=section,
                        code="repetition_too_dense",
                        message=(
                            f"Section '{section}' lặp dòng '{snippet}' {run} lần "
                            f"liên tiếp. Verse/bridge không nên loop hook — viết "
                            f"câu mới có chuyển động."
                        ),
                    )
                )

    # Imagery locales — only check when the field is present, since older
    # Lyricist prompts didn't always emit it. The Critic prompt separately
    # penalises a missing field.
    imagery = (
        contributions.get("imagery_locales_used")
        if isinstance(contributions, Mapping)
        else None
    )
    if language.lower() == "vi" and isinstance(imagery, list):
        non_empty = [str(x).strip() for x in imagery if str(x).strip()]
        concrete = [
            x for x in non_empty if x.lower() not in _GENERIC_IMAGERY_TOKENS
        ]
        if non_empty and (len(concrete) < 2):
            issues.append(
                LyricIssue(
                    section="imagery_locales_used",
                    code="imagery_too_generic",
                    message=(
                        "imagery_locales_used có < 2 chi tiết Việt cụ thể "
                        "(tên đường, địa danh, vật dụng đặc thù). Tránh "
                        "'mùa', 'đêm', 'trời', 'gió' chung chung — xem "
                        "imagery-locales-vn.md."
                    ),
                )
            )

    # Vietnamese tone-at-peak check. Composer specifies which section
    # carries the melodic peak (typically the chorus / hook). Lines in
    # that section ending on a *falling* tone (huyền / nặng) clash with
    # an ascending or sustained-high melody — the singer either has to
    # bend pitch awkwardly or the listener perceives the syllable as
    # "wrong word, wrong feeling". Lyric mismatch on V-pop tone-melody
    # is one of the most common Critic complaints; catching it here lets
    # us retry Lyricist before Critic ever sees the draft.
    if language.lower() == "vi":
        peak_section = _peak_section_from_composer(composer)
        if peak_section and peak_section in lyrics:
            peak_text = lyrics[peak_section]
            if isinstance(peak_text, str) and peak_text.strip():
                ratio, total_lines, offenders = _falling_tone_ratio(peak_text)
                # Need at least 2 lines to draw a meaningful conclusion;
                # a 1-line stub gets caught by ``too_short`` already.
                if total_lines >= 2 and ratio > _FALLING_TONE_THRESHOLD:
                    sample = " | ".join(
                        ln[:50] + ("…" if len(ln) > 50 else "")
                        for ln in offenders
                    )
                    issues.append(
                        LyricIssue(
                            section=peak_section,
                            code="tone_at_peak_falling",
                            message=(
                                f"Section '{peak_section}' (peak melody) có "
                                f"{int(ratio * 100)}% dòng kết bằng thanh "
                                f"huyền/nặng — kéo cao độ xuống tại nốt cao. "
                                f"Đổi từ cuối sang ngang/sắc/ngã. "
                                f"Ví dụ: {sample}"
                            ),
                        )
                    )

    # Syllable count cross-check against Composer's ``syllables_per_phrase``.
    # Composer gives Lyricist a rhythmic skeleton (e.g. chorus = [7,7,8,8]
    # syllables per line); if Lyricist writes a 12-syllable line where
    # Composer asked for 7, the line cannot be sung over the melody.
    spec = _syllables_per_phrase_from_composer(composer)
    if spec:
        for section_key, expected in spec.items():
            if section_key not in lyrics:
                continue
            raw_section_text = lyrics[section_key]
            if not isinstance(raw_section_text, str) or not raw_section_text.strip():
                continue
            actual_lines = _section_lyric_lines(raw_section_text)
            actual_counts = [len(_vn_syllables(ln)) for ln in actual_lines]

            # Spec gives N target counts. Compare line-by-line up to N
            # (extra lines beyond N are tolerated — Lyricist may add a
            # tag/echo line; missing lines under N are caught).
            mismatches: list[str] = []
            n = min(len(expected), len(actual_counts))
            for i in range(n):
                want = expected[i]
                got = actual_counts[i]
                if abs(got - want) > _SYLLABLE_TOLERANCE:
                    line_preview = actual_lines[i][:40] + (
                        "…" if len(actual_lines[i]) > 40 else ""
                    )
                    mismatches.append(
                        f"L{i + 1}: got {got}, expected {want} ('{line_preview}')"
                    )
            # Also flag when Lyricist wrote *fewer* lines than Composer
            # asked for — Composer's count IS the structural skeleton.
            if len(actual_counts) < len(expected):
                mismatches.append(
                    f"thiếu {len(expected) - len(actual_counts)} dòng so với "
                    f"spec ({len(actual_counts)}/{len(expected)})"
                )

            if mismatches:
                issues.append(
                    LyricIssue(
                        section=section_key,
                        code="syllable_count_mismatch",
                        message=(
                            f"Section '{section_key}' không khớp "
                            f"syllables_per_phrase của Composer "
                            f"(±{_SYLLABLE_TOLERANCE} syllable cho phép). "
                            f"{'; '.join(mismatches[:3])}"
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
