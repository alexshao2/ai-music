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


# --- Cliché bank file loading ---------------------------------------------


def test_cliche_bank_loaded_from_knowledge_file() -> None:
    """The cliché list must include phrases from cliche-bank-vn.md beyond
    the hardcoded fallback (we shipped a knowledge file with > 12 entries
    deliberately so the validator has wider coverage)."""
    from app.services.lyric_quality import _CLICHE_FALLBACK, _CLICHE_PHRASES

    # File-loaded list must be at least as broad as the fallback.
    assert len(_CLICHE_PHRASES) >= len(_CLICHE_FALLBACK)
    # Spot-check phrases that exist only in the markdown bank, not the
    # fallback — proves we are actually reading the file.
    bank_only = {
        "biển nhớ em",
        "mùa thu hà nội",
        "bóng cha già",
        "tết về sum vầy",
    }
    assert bank_only & set(_CLICHE_PHRASES), (
        f"Expected at least one of {bank_only} in loaded cliché bank, "
        f"got {sorted(_CLICHE_PHRASES)[:5]}..."
    )


def test_cliche_bank_parser_handles_empty_md() -> None:
    from app.services.lyric_quality import _parse_cliche_bank

    assert _parse_cliche_bank("") == []
    # Header-only table → no data rows.
    assert _parse_cliche_bank("| Cliché | Why |\n|--|--|\n") == []


def test_cliche_bank_parser_skips_template_rows() -> None:
    """Phrasing-cliché rows with ``___`` slot markers can't be regex-matched
    so we drop them from the bank."""
    from app.services.lyric_quality import _parse_cliche_bank

    md = (
        "| Cliché | Thay bằng |\n"
        "|--|--|\n"
        '| "Anh yêu em ___ / Mà em không hiểu" | ... |\n'
        '| "Em là duy nhất" | ... |\n'
    )
    parsed = _parse_cliche_bank(md)
    assert "em là duy nhất" in parsed
    assert all("___" not in p for p in parsed)


def test_validate_lyrics_flags_bank_loaded_cliche() -> None:
    """A cliché present in the markdown file (but NOT in the fallback)
    must trigger the validator — proves the file load is wired all the
    way through to the issue list."""
    bad = {
        "lyrics": {
            "verse_1": "Em là duy nhất trong cuộc đời tôi mãi mãi không quên",
            "pre_chorus": "Gió vẫn thổi qua căn phòng nhỏ của tôi",
            "chorus": "Tách trà nguội ngắt — tôi đếm phút em thương",
            "bridge": "Và tôi vẫn đi qua con phố cũ hôm nào",
        }
    }
    issues = validate_lyrics(bad, language="vi")
    cliche = [i for i in issues if i.code == "cliche_detected"]
    assert cliche, "Expected 'em là duy nhất' to be flagged as cliché"


# --- Vietnamese tone-at-peak validator ------------------------------------


def test_classify_vn_tone_recognises_all_six_tones() -> None:
    from app.services.lyric_quality import _classify_vn_tone

    assert _classify_vn_tone("ma") == "ngang"
    assert _classify_vn_tone("má") == "sắc"
    assert _classify_vn_tone("mà") == "huyền"
    assert _classify_vn_tone("mả") == "hỏi"
    assert _classify_vn_tone("mã") == "ngã"
    assert _classify_vn_tone("mạ") == "nặng"


def test_classify_vn_tone_works_on_decomposed_input() -> None:
    """Some LLM JSON encodings emit NFD; ensure we still classify."""
    import unicodedata

    from app.services.lyric_quality import _classify_vn_tone

    nfd = unicodedata.normalize("NFD", "thương")
    assert _classify_vn_tone(nfd) == "ngang"
    nfd_grave = unicodedata.normalize("NFD", "buồn")
    assert _classify_vn_tone(nfd_grave) == "huyền"


def test_validate_lyrics_flags_falling_tones_at_peak() -> None:
    """Composer says peak is the chorus, but every chorus line ends on a
    falling tone (huyền/nặng) — should trigger tone_at_peak_falling."""
    bad = {
        "lyrics": {
            "verse_1": "Tháng tư nắng vương trên Lê Văn Sỹ trên bàn nhỏ",
            "pre_chorus": "Gió vẫn thổi qua căn phòng nhỏ của tôi đêm nay",
            "chorus": (
                "Em đi rồi tôi nhớ buồn\n"          # huyền
                "Phố cũ giờ chỉ một mình\n"          # huyền (cuối "mình")
                "Tách trà nguội nằm trên bàn\n"     # huyền (cuối "bàn")
                "Tôi đếm phút giây trôi xa dần"      # huyền (cuối "dần")
            ),
            "bridge": "Và tôi vẫn đi qua con phố cũ hôm nào nhỏ",
        }
    }
    composer = {"peak_section": "chorus"}
    issues = validate_lyrics(bad, language="vi", composer=composer)
    tone = [i for i in issues if i.code == "tone_at_peak_falling"]
    assert tone, "Expected tone_at_peak_falling on chorus"
    assert tone[0].section == "chorus"


def test_validate_lyrics_passes_when_peak_endings_are_rising() -> None:
    """Same chorus rewritten with ngang/sắc endings — no tone issue."""
    good = {
        "lyrics": {
            "verse_1": "Tháng tư nắng vương trên Lê Văn Sỹ trên bàn",
            "pre_chorus": "Gió vẫn thổi qua căn phòng nhỏ của tôi",
            "chorus": (
                "Em đi rồi tôi nhớ thương\n"     # ngang
                "Phố cũ giờ chỉ riêng mình ta\n"  # ngang
                "Tách trà còn trên bàn em\n"      # ngang
                "Tôi đếm phút giây qua mãi"       # sắc
            ),
            "bridge": "Và tôi vẫn đi qua con phố cũ hôm nào nhỏ",
        }
    }
    composer = {"peak_section": "chorus"}
    issues = validate_lyrics(good, language="vi", composer=composer)
    assert not any(i.code == "tone_at_peak_falling" for i in issues)


def test_validate_lyrics_skips_tone_check_without_composer() -> None:
    """Without a Composer contribution, we don't know the peak section
    and shouldn't fabricate a check."""
    issues = validate_lyrics(
        {
            "lyrics": {
                "verse_1": "Tháng tư nắng vương trên Lê Văn Sỹ vào buồn",
                "pre_chorus": "Gió vẫn thổi qua căn phòng nhỏ của tôi",
                "chorus": "Em đi rồi tôi nhớ buồn\nPhố cũ giờ buồn\nTrà bàn buồn",
                "bridge": "Và tôi vẫn đi qua con phố cũ hôm nào nhỏ",
            }
        },
        language="vi",
        composer=None,
    )
    assert not any(i.code == "tone_at_peak_falling" for i in issues)


def test_validate_lyrics_skips_tone_check_for_non_vi_language() -> None:
    issues = validate_lyrics(
        {
            "lyrics": {
                "verse_1": "April sun on the table next to her",
                "pre_chorus": "Wind is blowing through the room every night",
                "chorus": (
                    "She is gone away tonight\n"
                    "Empty cup is on the side\n"
                    "Half the bed is cold and white\n"
                    "I remember every night"
                ),
                "bridge": "And I walk past the corner shop again",
            }
        },
        language="en",
        composer={"peak_section": "chorus"},
    )
    assert not any(i.code == "tone_at_peak_falling" for i in issues)


# --- Syllable count cross-check -------------------------------------------


def test_validate_lyrics_flags_syllable_count_mismatch() -> None:
    """Composer says chorus has 7-syllable lines; Lyricist writes 12-syllable
    lines — that's unsingable."""
    bad = {
        "lyrics": {
            "verse_1": "Tháng tư nắng vương trên Lê Văn Sỹ vào bàn",
            "pre_chorus": "Gió vẫn thổi qua căn phòng nhỏ của tôi",
            "chorus": (
                "Em đi rồi tôi vẫn ngồi đây mỗi đêm dài đếm\n"     # 12
                "Phố cũ giờ chỉ một mình tôi nhớ về em mãi"        # 11
            ),
            "bridge": "Và tôi vẫn đi qua con phố cũ hôm nào nhỏ",
        }
    }
    composer = {"syllables_per_phrase": {"chorus": [7, 7]}}
    issues = validate_lyrics(bad, language="vi", composer=composer)
    syl = [i for i in issues if i.code == "syllable_count_mismatch"]
    assert syl
    assert syl[0].section == "chorus"
    assert "got 12" in syl[0].message or "got 11" in syl[0].message


def test_validate_lyrics_tolerates_off_by_one_syllable() -> None:
    """±1 syllable is fine — Composer's spec is approximate."""
    okayish = {
        "lyrics": {
            "verse_1": "Tháng tư nắng vương trên Lê Văn Sỹ",
            "pre_chorus": "Gió vẫn thổi qua căn phòng nhỏ của tôi",
            "chorus": (
                "Em đi rồi tôi vẫn ngồi đây\n"   # 8 (spec says 7)
                "Phố cũ giờ chỉ riêng mình ta"   # 7 (spec)
            ),
            "bridge": "Và tôi vẫn đi qua con phố cũ hôm nào nhỏ",
        }
    }
    composer = {"syllables_per_phrase": {"chorus": [7, 7]}}
    issues = validate_lyrics(okayish, language="vi", composer=composer)
    assert not any(i.code == "syllable_count_mismatch" for i in issues)


def test_validate_lyrics_flags_too_few_lines() -> None:
    """Composer asked for 4 lines, Lyricist wrote 2 — flag the gap."""
    short = {
        "lyrics": {
            "verse_1": "Tháng tư nắng vương trên Lê Văn Sỹ vào bàn",
            "pre_chorus": "Gió vẫn thổi qua căn phòng nhỏ của tôi",
            "chorus": (
                "Em đi rồi tôi nhớ thương\n"
                "Phố cũ giờ chỉ riêng mình ta"
            ),
            "bridge": "Và tôi vẫn đi qua con phố cũ hôm nào nhỏ",
        }
    }
    composer = {"syllables_per_phrase": {"chorus": [6, 7, 7, 7]}}
    issues = validate_lyrics(short, language="vi", composer=composer)
    syl = [i for i in issues if i.code == "syllable_count_mismatch"]
    assert syl
    assert "thiếu" in syl[0].message  # "missing N lines"


def test_validate_lyrics_skips_syllable_check_without_spec() -> None:
    """Composer didn't provide syllables_per_phrase → no check."""
    issues = validate_lyrics(
        _GOOD_LYRICS,
        language="vi",
        composer={"peak_section": "chorus"},  # no syllables_per_phrase
    )
    assert not any(i.code == "syllable_count_mismatch" for i in issues)


def test_validate_lyrics_accepts_syllable_spec_with_scalar() -> None:
    """If Composer accidentally returns a scalar instead of a list, we
    treat it as a single-line spec rather than crashing."""
    issues = validate_lyrics(
        {
            "lyrics": {
                "verse_1": "Một dòng thôi",
                "pre_chorus": "Gió vẫn thổi qua căn phòng nhỏ của tôi",
                "chorus": "Tách trà nguội ngắt — tôi đếm phút em thương",
                "bridge": "Và tôi vẫn đi qua con phố cũ hôm nào nhỏ",
            }
        },
        language="vi",
        composer={"syllables_per_phrase": {"verse_1": 3}},
    )
    # 3-syllable spec, "Một dòng thôi" = 3 syllables → match.
    assert not any(i.code == "syllable_count_mismatch" for i in issues)
