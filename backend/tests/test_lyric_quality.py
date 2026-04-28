"""Tests for the Lyricist programmatic validator + retry nudge."""
from __future__ import annotations

from app.services.lyric_quality import (
    format_issues_for_retry,
    validate_lyrics,
)

_GOOD_LYRICS = {
    "lyrics": {
        "verse_1": (
            "Tháng tư nắng vương trên Lê Văn Sỹ\n"
            "Em đi rồi, tách trà nguội ngắt\n"
            "Tôi đếm lại từng phút em thương\n"
            "Lòng vẫn còn vương vài câu hỏi"
        ),
        "pre_chorus": (
            "Gió vẫn thổi qua căn phòng nhỏ\n"
            "Những ký ức cũ vẫn còn đây"
        ),
        "chorus": (
            "Tháng tư về trên Hai Bà Trưng\n"
            "Em đi rồi nắng vẫn còn vương\n"
            "Tách trà nguội ngắt trên bàn nhỏ\n"
            "Tôi đếm lại từng phút em thương"
        ),
        "bridge": (
            "Và tôi vẫn đi qua con phố cũ\n"
            "Nhớ ngày em còn ngồi bên tôi"
        ),
    },
    "hook_line": "Tháng tư về trên Hai Bà Trưng",
}


def test_validate_lyrics_accepts_clean_output() -> None:
    assert validate_lyrics(_GOOD_LYRICS, language="vi") == []


def test_validate_lyrics_flags_placeholder() -> None:
    bad = {
        "lyrics": {
            "verse_1": "[chờ Lyricist điền]",
            "pre_chorus": "Gió vẫn thổi qua căn phòng nhỏ của tôi",
            "chorus": "Em đi rồi, lòng tôi vẫn thương",
            "bridge": "Và tôi vẫn đi qua con phố cũ hôm nào",
        },
        "hook_line": "Em đi rồi",
    }
    issues = validate_lyrics(bad, language="vi")
    codes = {i.code for i in issues}
    assert "placeholder" in codes
    sections = {i.section for i in issues}
    assert "verse_1" in sections


def test_validate_lyrics_flags_schema_template_echo() -> None:
    bad = {
        "lyrics": {
            "verse_1": "<full lyric block. Plain lines separated by \\n>",
            "pre_chorus": "Gió vẫn thổi qua căn phòng nhỏ của tôi",
            "chorus": "Em đi rồi, lòng tôi vẫn thương",
            "bridge": "Và tôi vẫn đi qua con phố cũ hôm nào",
        }
    }
    issues = validate_lyrics(bad, language="vi")
    assert any(i.code == "placeholder" and i.section == "verse_1" for i in issues)


def test_validate_lyrics_flags_empty_section() -> None:
    bad = {
        "lyrics": {
            "verse_1": "",
            "pre_chorus": "Gió vẫn thổi qua căn phòng nhỏ của tôi",
            "chorus": "Em đi rồi, lòng tôi vẫn thương nhau",
            "bridge": "Và tôi vẫn đi qua con phố cũ hôm nào",
        }
    }
    issues = validate_lyrics(bad, language="vi")
    codes = {(i.section, i.code) for i in issues}
    assert ("verse_1", "empty_section") in codes


def test_validate_lyrics_flags_missing_vi_diacritics() -> None:
    bad = {
        "lyrics": {
            "verse_1": "She walks away in the April rain alone today",
            "pre_chorus": "Gió vẫn thổi qua căn phòng nhỏ của tôi",
            "chorus": "Em đi rồi, lòng tôi vẫn thương nhau",
            "bridge": "Và tôi vẫn đi qua con phố cũ hôm nào",
        }
    }
    issues = validate_lyrics(bad, language="vi")
    assert any(i.code == "wrong_language" for i in issues)


def test_validate_lyrics_allows_english_for_en_brief() -> None:
    en = {
        "lyrics": {
            "verse_1": "She walks away in the April rain alone today",
            "pre_chorus": "The wind still blows through empty halls",
            "chorus": "Her silhouette is burning in my memory tonight",
            "bridge": "And I keep walking down these old familiar streets",
        }
    }
    assert validate_lyrics(en, language="en") == []


def test_format_issues_for_retry_is_actionable() -> None:
    bad = {"lyrics": {}}
    issues = validate_lyrics(bad, language="vi")
    nudge = format_issues_for_retry(issues)
    assert "LẦN TRƯỚC" in nudge
    assert "JSON" in nudge
    # Empty list should produce empty nudge (no-op).
    assert format_issues_for_retry([]) == ""


def test_validate_lyrics_missing_lyrics_object() -> None:
    issues = validate_lyrics({"hook_line": "oh oh"}, language="vi")
    assert any(i.code == "missing_lyrics" for i in issues)


def test_validate_lyrics_flags_cliche_in_section() -> None:
    bad = {
        "lyrics": {
            "verse_1": (
                "Tháng tư về phố cũ Hai Bà Trưng\n"
                "Tôi vẫn còn lạc lõng giữa đám đông\n"
                "Đếm ngược từng phút em đi rất xa"
            ),
            "pre_chorus": "Gió vẫn thổi qua căn phòng nhỏ của tôi",
            "chorus": (
                "Trái tim tan vỡ đêm nay tôi không ngủ\n"
                "Nhớ em nhiều như mưa chiều Hà Nội\n"
                "Tôi xếp lại từng câu em đã nói"
            ),
            "bridge": "Và tôi vẫn đi qua con phố cũ hôm nào",
        }
    }
    issues = validate_lyrics(bad, language="vi")
    cliche_issues = [i for i in issues if i.code == "cliche_detected"]
    sections = {i.section for i in cliche_issues}
    assert "verse_1" in sections
    assert "chorus" in sections
    assert any("lạc lõng giữa đám đông" in i.message for i in cliche_issues)
    assert any("trái tim tan vỡ" in i.message for i in cliche_issues)


def test_validate_lyrics_skips_cliche_check_for_english() -> None:
    en = {
        "lyrics": {
            "verse_1": "She walks away in the April rain alone today",
            "pre_chorus": "The wind still blows through empty halls of mine",
            "chorus": "My heart is broken and I cannot sleep tonight at all",
            "bridge": "And I keep walking down these old familiar streets",
        }
    }
    issues = validate_lyrics(en, language="en")
    assert not any(i.code == "cliche_detected" for i in issues)


def test_validate_lyrics_flags_imagery_too_generic() -> None:
    bad = {
        "lyrics": {
            "verse_1": "Tháng tư nắng vương trên Lê Văn Sỹ vẫn còn vương",
            "pre_chorus": "Gió vẫn thổi qua căn phòng nhỏ của tôi",
            "chorus": "Tách trà nguội ngắt — tôi đếm phút em thương",
            "bridge": "Và tôi vẫn đi qua con phố cũ hôm nào",
        },
        "imagery_locales_used": ["mùa", "đêm"],
    }
    issues = validate_lyrics(bad, language="vi")
    codes = {(i.section, i.code) for i in issues}
    assert ("imagery_locales_used", "imagery_too_generic") in codes


def test_validate_lyrics_accepts_concrete_imagery_list() -> None:
    """When imagery_locales_used has ≥2 concrete entries, no issue raised."""
    good = {
        "lyrics": {
            "verse_1": "Tháng tư nắng vương trên Lê Văn Sỹ vẫn còn vương",
            "pre_chorus": "Gió vẫn thổi qua căn phòng nhỏ của tôi",
            "chorus": "Tách trà nguội ngắt — tôi đếm phút em thương",
            "bridge": "Và tôi vẫn đi qua con phố cũ hôm nào",
        },
        "imagery_locales_used": ["Lê Văn Sỹ", "tách trà", "mùa"],
    }
    issues = validate_lyrics(good, language="vi")
    assert not any(i.code == "imagery_too_generic" for i in issues)


def test_validate_lyrics_skips_imagery_when_field_absent() -> None:
    """Backward compat: missing imagery_locales_used must not raise."""
    no_field = {
        "lyrics": {
            "verse_1": "Tháng tư nắng vương trên Lê Văn Sỹ vẫn còn vương",
            "pre_chorus": "Gió vẫn thổi qua căn phòng nhỏ của tôi",
            "chorus": "Tách trà nguội ngắt — tôi đếm phút em thương",
            "bridge": "Và tôi vẫn đi qua con phố cũ hôm nào",
        }
    }
    issues = validate_lyrics(no_field, language="vi")
    assert not any(i.code == "imagery_too_generic" for i in issues)


def test_validate_lyrics_flags_consecutive_repetition_in_verse() -> None:
    bad = {
        "lyrics": {
            "verse_1": (
                "Em đi rồi tôi vẫn ngồi đây\n"
                "Em đi rồi tôi vẫn ngồi đây\n"
                "Em đi rồi tôi vẫn ngồi đây"
            ),
            "pre_chorus": "Gió vẫn thổi qua căn phòng nhỏ của tôi",
            "chorus": "Tách trà nguội ngắt — tôi đếm phút em thương",
            "bridge": "Và tôi vẫn đi qua con phố cũ hôm nào",
        }
    }
    issues = validate_lyrics(bad, language="vi")
    rep = [i for i in issues if i.code == "repetition_too_dense"]
    assert rep, "expected repetition_too_dense issue on verse_1"
    assert rep[0].section == "verse_1"


def test_validate_lyrics_allows_chorus_repetition() -> None:
    """Chorus can legitimately repeat its hook line several times."""
    chorus_loop = {
        "lyrics": {
            "verse_1": "Tháng tư nắng vương trên Lê Văn Sỹ vẫn còn vương",
            "pre_chorus": "Gió vẫn thổi qua căn phòng nhỏ của tôi",
            "chorus": (
                "Em đi rồi tôi vẫn ngồi đây\n"
                "Em đi rồi tôi vẫn ngồi đây\n"
                "Em đi rồi tôi vẫn ngồi đây"
            ),
            "bridge": "Và tôi vẫn đi qua con phố cũ hôm nào",
        }
    }
    issues = validate_lyrics(chorus_loop, language="vi")
    assert not any(i.code == "repetition_too_dense" for i in issues)
