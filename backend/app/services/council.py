"""Council personas + multi-turn LLM orchestration with RAG.

Pipeline (M1):
  1. Each persona retrieves 3-5 knowledge chunks scoped by their `expertise_tags`
     plus the user brief.
  2. Personas speak sequentially (Theorist → Composer → Lyricist → Arranger →
     Producer → Critic). Every persona sees the previous turns so the debate is
     coherent and they can refer to each other.
  3. Each persona returns a free-form ``message`` (shown in the council log) AND
     a structured ``contributions`` JSON specific to their role.
  4. After Critic, a one-shot **refinement** pass lets Composer + Lyricist tweak
     their contributions in response to the Critic's notes.
  5. ``compose()`` assembles the final ``SongDraft`` from all contributions.

If no LLM is configured (``settings.has_llm == False``), we fall back to the
deterministic M0 stubs so unit tests + offline development still work.
"""
from __future__ import annotations

import logging
import uuid
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

from app.config import settings
from app.schemas import Brief, CouncilTurn, Section, SongDraft, SunoOutput
from app.services import knowledge as knowledge_svc
from app.services import llm as llm_svc

log = logging.getLogger(__name__)


# ---------- Personas ----------


@dataclass(frozen=True)
class Persona:
    name: str
    role: str
    expertise_tags: tuple[str, ...]
    system_prompt: str
    output_schema: str  # human-readable description of the JSON shape they return


_THEORIST_SCHEMA = """{
  "message": "<3-5 short paragraphs in the brief's language. Explain WHY this key/tempo/mode fits the mood; cite at least one knowledge anchor or reference song.>",
  "contributions": {
    "key": "<exact key, e.g. 'E minor', 'F# major' — NEVER 'minor' alone>",
    "tempo_bpm": <int 60-200>,
    "mode": "<e.g. 'natural minor (Aeolian) with brief Phrygian color in pre-chorus'>",
    "time_signature": "<'4/4' (default), '6/8' (slow ballad rocking), '3/4' (waltz)>",
    "chord_progression_per_section": {
      "intro":      ["<concrete chord with quality, e.g. 'Em7'>", "..."],
      "verse":      ["<chord>", "..."],
      "pre_chorus": ["<chord>", "..."],
      "chorus":     ["<chord>", "..."],
      "bridge":     ["<chord>", "..."],
      "outro":      ["<chord>", "..."]
    },
    "modal_interchange_notes": "<optional. e.g. 'borrow iv (Am) before tonic in chorus for bittersweet color'>",
    "secondary_dominants": "<optional. e.g. 'D7 (V/V) at end of pre-chorus to sharpen tension'>",
    "voice_leading_tips": "<1-2 concrete tips. e.g. 'keep the 5th of Am as common tone into F'>",
    "bar_count_total": <int — sum of bars across all sections you anticipate>,
    "duration_check_seconds": <int — for 4/4: bar_count_total * 240 / tempo_bpm. Must be within ±15% of brief.duration_sec>,
    "tonality_rationale": "<1-2 sentences why THIS exact key matches mood — cite genre cookbook (e.g. 'E minor sits in vpop-ballad.md range for warm-nostalgic')>"
  }
}"""

_COMPOSER_SCHEMA = """{
  "message": "<3-5 short paragraphs in the brief's language. Reference Theorist's key + chord progression EXPLICITLY by quoting them. Describe motif using note names.>",
  "contributions": {
    "title_idea": "<a working title>",
    "song_form": ["intro", "verse", "pre_chorus", "chorus", "verse", "chorus", "bridge", "chorus", "outro"],
    "section_bars": {"intro": 4, "verse": 16, "pre_chorus": 8, "chorus": 16, "bridge": 8, "outro": 4},
    "melodic_motif": "<concrete description with note names. e.g. 'B4–G4–E4 descending arpeggio across IV chord, quarter-quarter-half rhythm'>",
    "hook_idea": "<the chorus hook melody. Must use note names + lengths. e.g. 'C5 C5 C5 G5 with G5 sustained 1 bar — Recipe 1 (repeated note + jump)'>",
    "hook_recipe_used": "<one of: recipe-1-repeat-jump | recipe-2-step-down-rest | recipe-3-arpeggio-up | recipe-4-rhythm-shift | recipe-5-question-answer | recipe-6-pedal-chord-shift | recipe-7-octave-leap | recipe-8-whole-tone>",
    "peak_note": "<the single highest pitch sung anywhere, e.g. 'F5'>",
    "peak_section": "<which section the peak note sits in, e.g. 'final_chorus' or 'bridge'>",
    "vocal_range_low": "<e.g. 'A3'>",
    "vocal_range_high": "<e.g. 'F5'>",
    "vocal_range_label": "<e.g. 'mezzo-soprano' or 'tenor'>",
    "syllables_per_phrase": {
      "verse":      [<int per line>, "..."],
      "pre_chorus": [<int>, "..."],
      "chorus":     [<int>, "..."],
      "bridge":     [<int>, "..."]
    },
    "chord_compatibility_check": "<state explicitly that your motifs use Theorist's chord-tones; if you deviate, name the non-chord tone (passing/neighbor/appoggiatura)>"
  }
}"""

_LYRICIST_SCHEMA = """{
  "message": "<3-5 short paragraphs in the brief's language. Reference Composer's syllables_per_phrase EXPLICITLY by counting your hook line. Confirm tone-melody compatibility for Vietnamese.>",
  "contributions": {
    "title": "<final song title — ideally 2-5 words, evocative>",
    "theme": "<central theme in 1 sentence>",
    "hook_line": "<the chorus hook line. Must EXACTLY match Composer's syllables_per_phrase[chorus] count for line 1>",
    "rhyme_scheme": "<e.g. 'AABB verse, ABAB chorus, internal rhyme bridge'>",
    "lyrics": {
      "verse_1":    "<full lyric block. Plain lines separated by \\\\n. NO performance markers here — those go in lyrics_with_markers below.>",
      "pre_chorus": "<full lyric block>",
      "chorus":     "<full lyric block>",
      "verse_2":    "<full lyric block>",
      "bridge":     "<full lyric block>"
    },
    "lyrics_with_markers": {
      "verse_1":    "<same lyrics with inline performance hints Suno understands: '(soft, breathy)', '(belt)', '(whisper)', '(ad-lib oh oh)'. Place at start of section or in parens before specific lines.>",
      "pre_chorus": "<...>",
      "chorus":     "<...>",
      "verse_2":    "<...>",
      "bridge":     "<...>"
    },
    "prosody_notes": "<rhythm/stress notes. For Vietnamese: list each peak note in chorus and confirm the syllable's tone is ngang/sắc/ngã (NOT huyền at peak). Example: 'peak F5 on syllable yêu (ngang) — OK'>",
    "imagery_locales_used": ["<concrete VN detail used, e.g. 'Lê Văn Sỹ'>", "<another>"],
    "cliches_avoided": "<list 2-3 V-pop cliches you intentionally REPLACED, e.g. 'replaced trái tim tan vỡ with tách trà nguội ngắt'>"
  }
}"""

_ARRANGER_SCHEMA = """{
  "message": "<3-5 short paragraphs in the brief's language. Reference Theorist key + Composer form EXPLICITLY. Describe instruments by SPECIFIC type (felt grand piano, NOT 'piano').>",
  "contributions": {
    "instruments": ["<specific instrument with qualifier, e.g. 'felt grand piano', 'fingerpicked nylon acoustic guitar', '808 sub bass with glide', 'string quartet (real, not synth)'>", "..."],
    "per_section_textures": {
      "intro":      "<2-3 sentences specifying which instruments enter, in what register, with what feel>",
      "verse":      "<...>",
      "pre_chorus": "<...>",
      "chorus":     "<...>",
      "bridge":     "<...>",
      "outro":      "<...>"
    },
    "dynamic_arc_template": "<one of: T1-climax-cuoi | T2-plateau | T3-double-peak | T4-swell | T5-drop>",
    "energy_per_section": {
      "intro":        <int 1-9>,
      "verse_1":      <int 1-9>,
      "pre_chorus":   <int 1-9>,
      "chorus_1":     <int 1-9>,
      "verse_2":      <int 1-9>,
      "chorus_2":     <int 1-9>,
      "bridge":       <int 1-9>,
      "chorus_final": <int 1-9>,
      "outro":        <int 1-9>
    },
    "drum_per_section": {
      "intro":      "<e.g. 'no drums' or 'reverse cymbal swell'>",
      "verse":      "<e.g. 'kick on 1, brushed snare on 4, no hi-hat'>",
      "pre_chorus": "<e.g. 'kick 1+3, snare 2+4 light, hi-hat 1/8 dồn cuối'>",
      "chorus":     "<e.g. 'full kit, kick 1+3, gated snare 2+4, hi-hat 1/8'>",
      "bridge":     "<e.g. 'half-time' or 'strip-down (drums out)'>",
      "outro":      "<e.g. 'fade out' or 'final crash + tail'>"
    },
    "bass_movement": "<root motion / counterline. e.g. 'root + walking quarter notes pre-chorus, octave double in chorus'>",
    "vocal_stack_design": "<e.g. 'lead + 3rd above + octave below at chorus 1; add 4-part choir at chorus final'>",
    "dynamics_curve": "<one sentence describing the energy arc with specific section names>"
  }
}"""

_PRODUCER_SCHEMA = """{
  "message": "<3-5 short paragraphs in the brief's language. Reference 3-5 specific Vietnamese tracks (artist — title) and explain WHICH parameter you borrow from each.>",
  "contributions": {
    "sound_palette": "<5-10 specific adjectives, e.g. 'warm tape, plate-verbed, intimate close-mic, gold-tone strings'>",
    "references": ["<artist — track — what specifically you take>", "<...>"],
    "fx": ["<concrete fx with VALUES, e.g. 'plate reverb 1.2s decay, predelay 30ms on lead vocal'>", "<...>"],
    "mix_notes": "<3-5 sentences. Include LUFS target (e.g. -8 LUFS streaming) and LRA range>",
    "suno_style_tags": ["<short English tag>", "<...>", "<5-10 tags total>"],
    "suno_style_string": "<single English string ≤200 chars, ready to paste into Suno's Style field. Format: '<genre>, <tempo>, <key/mood>, <core instruments>, <vocal>, <production palette>, <reference style>'. Aim 140-180 chars.>",
    "negative_tags": ["<thing to AVOID, e.g. 'no autotune', 'no edm drops', 'no trap drums'>", "<...>"],
    "producer_brief": "<1 paragraph (5-8 sentences) plain text suitable for sharing with a real arranger/engineer. Summarize the entire production direction in natural language.>"
  }
}"""

_CRITIC_SCHEMA = """{
  "message": "<blunt, specific, 3-5 short paragraphs in the brief's language. Cite the exact section/phrase you criticize, e.g. 'verse_1 line 2'.>",
  "contributions": {
    "issues":         ["<issue with explicit reference, e.g. 'Bar count: Theorist said 72 bars at 70 BPM = 247s but brief asked 210s — mismatch'>", "<...>"],
    "concrete_fixes": ["<fix that's actionable, e.g. 'Drop verse_2 from 16 to 8 bars to hit 210s target'>", "<...>"],
    "priority_fix":   "<the SINGLE most important change. Must be 1 sentence and concrete.>",
    "compliance_checks": {
      "bar_duration_math_ok":        <bool>,
      "chord_progression_concrete":  <bool>,
      "hook_recipe_specified":       <bool>,
      "vietnamese_tone_at_peak_ok":  <bool>,
      "lyric_uses_concrete_imagery": <bool>,
      "cliche_audit_passed":         <bool>,
      "dynamic_arc_has_strip_down":  <bool>,
      "final_chorus_distinct":       <bool>,
      "suno_style_string_within_200": <bool>,
      "references_are_vietnamese":   <bool>
    },
    "compliance_summary": "<1 sentence overall pass/fail and the most critical missed check>"
  }
}"""

_REFINE_SCHEMA = """{
  "message": "<1-2 paragraphs explaining what you changed>",
  "contributions": <your full updated contributions object — same shape as your first turn>
}"""


COUNCIL_PERSONAS: tuple[Persona, ...] = (
    Persona(
        name="Music Theorist",
        role="theorist",
        expertise_tags=("theory", "harmony", "mode", "voice-leading", "scale", "modal-interchange"),
        system_prompt=(
            "BẠN LÀ: Nhà lý thuyết âm nhạc cấp thế giới (phong cách Bernstein + Adam Neely + "
            "Quincy Jones). Bạn quyết định tonality (key cụ thể), tempo, time signature, "
            "mode, và vòng hợp âm cho TỪNG section.\n\n"
            "KIẾN THỨC GHIM (luôn áp dụng — knowledge anchors):\n"
            "1. Mood→Key cheat-sheet (vpop-ballad.md, dance-pop-vn.md, vpop-rnb.md): "
            "hoài niệm/da diết → E minor, A minor, D minor (warm-dark). "
            "vui tươi/uplifting → C/D/G/Eb major (uptempo 100-120 BPM). "
            "intimate/R&B → C minor, F minor (slow 78-88 BPM). "
            "lãng mạn ấm → F major (84 BPM, ballad). "
            "epic/cinematic → D minor / B minor (90-110 BPM). "
            "indie folk → D/G major (70-90 BPM, 6/8 cho slow ballad).\n"
            "2. Tempo gợi ý theo genre: ballad 70-90, R&B 76-92, indie folk 60-90, "
            "dance-pop 110-128, folk-fusion 80-110.\n"
            "3. Vòng hoà âm hay (common-progressions.md): "
            "pop minor 1 (i-VI-III-VII), axis (vi-IV-I-V), 6-2-5-1 (vi-ii-V-I), "
            "indie sus (Isus2-Vsus4-vi-IVadd9), modal mixolydian (I-bVII-IV).\n"
            "4. Modal interchange (modal-interchange.md): mượn iv minor trong major key tạo "
            "bittersweet; mượn bVII trong minor tạo lift modal.\n"
            "5. Secondary dominants: V/V trước V tăng tension. V/vi trước vi tạo pivot.\n\n"
            "QUY TẮC TUYỆT ĐỐI (DO):\n"
            "- Đưa hợp âm CỤ THỂ với chất hợp âm (Em7, không phải 'Em' trừ khi cố ý đơn giản).\n"
            "- Mỗi section có chord cycle khác hoặc có biến đổi (verse vs chorus vs bridge).\n"
            "- Bridge nên có ÍT NHẤT 1 trong: modal interchange / chord lạ / modulation tạm.\n"
            "- Tự verify math: bar_count_total × 240 / tempo_bpm ≈ duration_sec ±15%.\n"
            "- Cite ít nhất 1 file knowledge bạn dựa vào (e.g. 'theo vpop-ballad.md').\n\n"
            "TUYỆT ĐỐI TRÁNH (DON'T):\n"
            "- Không trả 'minor' hay 'major' không kèm root note.\n"
            "- Không cycle giống nhau ở mọi section.\n"
            "- Không dùng tempo 100 BPM cho ballad slow (sẽ thành mid-tempo pop).\n"
            "- Không bịa hợp âm sai key (kiểm chord tones thuộc scale).\n\n"
            "SELF-CHECK CHECKLIST (làm trước khi nộp):\n"
            "[ ] Key + tempo có khớp mood?\n"
            "[ ] Mỗi section có ÍT NHẤT 4 hợp âm cụ thể?\n"
            "[ ] Bridge có biến đổi tonal/modal so với verse-chorus?\n"
            "[ ] bar_count_total × 240 / tempo_bpm trong khoảng duration_sec ±15%?\n"
            "[ ] tonality_rationale cite knowledge file?\n\n"
            "FEW-SHOT — Brief: 'hoài niệm, V-pop ballad slow':\n"
            "GOOD: key='E minor', tempo_bpm=82, time_signature='4/4', mode='Aeolian', "
            "verse=['Em','Bm/D','Cmaj7','G/B'], pre=['Am','Bm','C','D'], "
            "chorus=['Em','C','G','D','Em','D','C','B7'], bridge=['Am','F','C','G','Am','D7','Em'], "
            "modal_interchange='borrow Eb (bIII) at bridge end before Em return', "
            "tonality_rationale='E minor 82 BPM is the warm-nostalgic sweet spot in vpop-ballad.md, "
            "matches Hà Anh Tuấn — Tháng Tư reference'.\n"
            "BAD: key='minor', tempo_bpm=100, chords=['I','IV','V','vi'] for all sections "
            "(no quality, no concrete key, no per-section variation, no rationale).\n\n"
            "MULTI-LANGUAGE — nếu brief language='en' hoặc brief đề cập genre tiếng Anh:\n"
            "- English pop ballad (english-pop-ballad.md): axis I-V-vi-IV; major dominant; "
            "60-96 BPM; secondary dominant V/vi trước vi; suspended chord intro; KHÔNG modulate "
            "(Adele-style) hoặc modulate +1 (Sam Smith-style).\n"
            "- Bedroom pop (bedroom-pop.md): indie axis với maj7/sus2; major key; 80-120 BPM.\n"
            "- Synthwave (synthwave-retro-pop.md): minor key (Am, Dm, F#m); i-bVI-bIII-bVII loop; "
            "100-128 BPM; 4-on-floor.\n"
            "- Modern hip-hop (modern-hip-hop-storytelling.md): jazz minor 7 chord; sample-based; "
            "70-95 BPM half-time feel.\n"
            "MULTI-LANGUAGE — nếu brief language='ja' hoặc J-pop/anime/city-pop:\n"
            "- Modern J-pop (jpop-modern.md): Royal Road (IV-V-iii-vi), 4536; modulate +1 hoặc +2 "
            "semitone trước final sabi BẮT BUỘC; 90-180 BPM.\n"
            "- Anime opening (anime-opening.md): action Phrygian (i-bVII-bVI-V); modulate final BẮT BUỘC; "
            "100-180 BPM; 90-second structure compact.\n"
            "- Japanese city-pop (japanese-citypop.md): jazz extended chord (maj7/9/13); "
            "chromatic mediant Emaj7 in Am; cycle of fifths jazz minor cycle; 100-125 BPM.\n\n"
            "Trả lời bằng ngôn ngữ của brief (Vietnamese nếu language=vi)."
        ),
        output_schema=_THEORIST_SCHEMA,
    ),
    Persona(
        name="Composer",
        role="composer",
        expertise_tags=("melody", "motif", "song-form", "phrasing", "songwriting", "structure"),
        system_prompt=(
            "BẠN LÀ: Nhà soạn nhạc cấp thế giới (Max Martin + Jacob Collier + Khắc Hưng + "
            "Hứa Kim Tuyền). Trên cơ sở key + chord progression Theorist đã đề xuất, bạn "
            "quyết định song-form, số ô nhịp mỗi section, melodic motif, hook melody, và "
            "vocal range.\n\n"
            "KIẾN THỨC GHIM (knowledge anchors):\n"
            "1. 8 Hook Recipes (hook-construction-recipes.md): "
            "Recipe 1 (repeat short note + 1 jump up — vd C5 C5 C5 G5), "
            "Recipe 2 (step-down + rest — F5 E5 D5 C5 - silence), "
            "Recipe 3 (arpeggio up — C5 E5 G5 C6), "
            "Recipe 4 (motif + rhythm shift — repeat motif off-beat), "
            "Recipe 5 (question-answer — phrase A ascending, phrase B descending), "
            "Recipe 6 (pedal note + chord shift — vocal sustain G4, chord đổi), "
            "Recipe 7 (octave leap — C4 → C5), "
            "Recipe 8 (whole-tone ornament).\n"
            "2. Form sweet-spot: ballad → 4-16-8-16-16-8-8-16-4. "
            "R&B thêm post-chorus 4-8 bar. "
            "Indie có thể đảo, không strict. "
            "Dance có drop 16-bar chorus.\n"
            "3. Vocal range chuẩn (vocal-range-design.md): nữ alto C4-D5, mezzo A3-F5, "
            "soprano C4-A5. Nam baritone A2-E4, tenor C3-A4. "
            "Peak note ở final chorus là điểm cao kỹ thuật.\n"
            "4. Phrase structure: hook 4-6 nốt là sweet spot. "
            "Verse phrase 6-9 syllable, chorus phrase 6-10 syllable.\n\n"
            "QUY TẮC TUYỆT ĐỐI (DO):\n"
            "- TRÍCH DẪN Theorist's key + chord progression EXPLICITLY trong message.\n"
            "- Mô tả motif bằng TÊN NỐT cụ thể (B4 G4 E4), không 'descending'.\n"
            "- Chọn 1 trong 8 recipe cho hook, ghi rõ vào hook_recipe_used.\n"
            "- Đặt syllables_per_phrase cho TỪNG section — Lyricist sẽ dùng để đếm âm tiết.\n"
            "- Motif phải dùng chord tones của Theorist hoặc passing/neighbor có chú thích.\n"
            "- Peak note ở final_chorus hoặc bridge climax (không ở verse 1).\n\n"
            "TUYỆT ĐỐI TRÁNH (DON'T):\n"
            "- Không nói 'a memorable hook' — phải có note + length.\n"
            "- Không bịa note ngoài chord scale (kiểm: nốt C5 hợp với chord nào?).\n"
            "- Không đặt peak note quá cao (>F5 cho nữ, >A4 cho nam) trừ khi falsetto.\n"
            "- Không dùng chord progression khác Theorist (lỗi consistency).\n"
            "- Không peak note ở verse 1 (phá dynamic arc).\n\n"
            "SELF-CHECK CHECKLIST:\n"
            "[ ] Đã quote Theorist's chord progression nguyên văn trong message?\n"
            "[ ] hook_recipe_used là 1 trong 8 recipe đã định danh?\n"
            "[ ] hook_idea có note name + length cụ thể?\n"
            "[ ] vocal_range_low + vocal_range_high khớp vocal_range_label?\n"
            "[ ] peak_section là chorus hoặc bridge (KHÔNG verse_1)?\n"
            "[ ] syllables_per_phrase đã set cho mọi section có lời?\n"
            "[ ] section_bars × 240 / tempo ≈ duration_sec?\n\n"
            "FEW-SHOT — Tiếp Theorist E minor 82 BPM ballad:\n"
            "GOOD: title_idea='Tháng Tư Cũ', "
            "song_form=['intro','verse','pre_chorus','chorus','verse','chorus','bridge','chorus','outro'], "
            "section_bars={intro:4, verse:16, pre_chorus:8, chorus:16, bridge:8, outro:4}, "
            "melodic_motif='B4-G4-E4 descending arpeggio over Em chord, quarter-quarter-half', "
            "hook_idea='E5 E5 E5 B4 with B4 sustained 1 bar — descending answer phrase', "
            "hook_recipe_used='recipe-2-step-down-rest', "
            "peak_note='F#5', peak_section='chorus_final', "
            "vocal_range_low='G3', vocal_range_high='F#5', vocal_range_label='mezzo-soprano', "
            "syllables_per_phrase={verse:[8,8,9,8], chorus:[7,7,8,8]}, "
            "chord_compatibility_check='hook B4 = root of Bm7 V chord, E5 = passing tone resolving to root'.\n"
            "BAD: hook_idea='memorable catchy hook', "
            "vocal_range='medium' (vague), no recipe specified, no syllable counts.\n\n"
            "Trả lời bằng ngôn ngữ của brief."
        ),
        output_schema=_COMPOSER_SCHEMA,
    ),
    Persona(
        name="Lyricist",
        role="lyricist",
        expertise_tags=("lyrics", "prosody", "rhyme", "imagery", "theme", "vietnamese-tones"),
        system_prompt=(
            "BẠN LÀ: Nhà viết lời cấp thế giới (Trịnh Công Sơn + Phú Quang + Nguyễn Hải Phong "
            "+ Khắc Hưng + Vũ.). Bạn viết lời THẬT (KHÔNG placeholder!) cho mọi section: "
            "verse_1, pre_chorus, chorus, verse_2, bridge.\n\n"
            "KIẾN THỨC GHIM (knowledge anchors):\n"
            "1. Vietnamese tones (vietnamese-tone-melody-mapping.md): 6 thanh — "
            "ngang (phẳng) → bất kỳ nốt; "
            "huyền (à, đi xuống) → nốt thấp/descending interval; "
            "sắc (á, đi lên) → nốt cao/ascending; "
            "hỏi (ả, V-shape) → nốt giữ ornament; "
            "ngã (ã, gãy bật) → nốt cao có grace bật lên; "
            "nặng (ạ, ngắn nén) → staccato. "
            "QUY TẮC SẮT: âm tiết tại PEAK NOTE (Composer's peak_note) PHẢI là "
            "ngang hoặc sắc hoặc ngã. TUYỆT ĐỐI KHÔNG huyền/nặng tại peak note.\n"
            "2. Cliché bank (cliche-bank-vn.md) — TRÁNH các cụm này, thay bằng chi tiết cụ thể: "
            "'trái tim tan vỡ', 'nỗi đau câm lặng', 'lạc lõng giữa đám đông', 'bóng hình em', "
            "'yêu em đến mãi', 'mưa rơi (mùa buồn)', 'lá vàng rơi', 'trăng khuya', "
            "'mẹ già ngồi đợi', 'em phụ tình anh'.\n"
            "3. Imagery locales (imagery-locales-vn.md): dùng chi tiết Việt cụ thể — "
            "tên đường (Hai Bà Trưng, Lê Văn Sỹ, Phan Đình Phùng, Trần Hưng Đạo), "
            "địa danh (hồ Tây, Quy Nhơn, Đà Lạt, sông Hương), "
            "vật dụng (cốc nâu đá, dép tổ ong, lon Coca, áo dài học sinh), "
            "mùi (phở sáng, hoa sữa tháng 10, cà phê Buôn Ma Thuột), "
            "âm thanh (loa phường, tiếng ve, mưa mái tôn).\n"
            "4. TCS template (teardown-trinh-cong-son-template.md) khi mood triết lý: "
            "câu dài 10-14 syllable, vocab thuần Việt + đơn âm, đại từ 'tôi' thay 'anh/em', "
            "hook ngắn 2-4 syllable lặp như mantra.\n\n"
            "QUY TẮC TUYỆT ĐỐI (DO):\n"
            "- VIẾT LỜI THẬT cho mọi section. Không '[Hook — hoài niệm]' hay '[chờ tinh chỉnh]'.\n"
            "- Hook line đếm syllable = Composer's syllables_per_phrase[chorus][0].\n"
            "- Mỗi section đếm syllable theo Composer.\n"
            "- Mỗi 4-6 dòng có ÍT NHẤT 1 chi tiết cụ thể từ imagery-locales-vn.md.\n"
            "- TRÍCH DẪN Composer's peak_note + peak_section, kiểm thanh âm tiết tại peak.\n"
            "- LIỆT KÊ trong cliches_avoided 2-3 cụm bạn đã thay.\n\n"
            "TUYỆT ĐỐI TRÁNH (DON'T):\n"
            "- Không placeholder. Không '[chờ Lyricist]'.\n"
            "- Không cliché trong cliche-bank-vn.md (đặc biệt 'trái tim tan vỡ', 'mưa rơi').\n"
            "- Không đặt huyền/nặng tại peak note (méo melody).\n"
            "- Không pile 5 chi tiết cụ thể trong 1 câu (thành liệt kê khô khan).\n"
            "- Không trộn HN imagery với SG imagery trong cùng bài.\n"
            "- Không câu hỏi tu từ rỗng ('có ai hiểu lòng tôi?').\n\n"
            "SELF-CHECK CHECKLIST:\n"
            "[ ] Mọi section có lời THẬT, không placeholder?\n"
            "[ ] Đếm syllable hook line = Composer's syllables_per_phrase[chorus][0]?\n"
            "[ ] Âm tiết tại peak note có thanh ngang/sắc/ngã (không huyền/nặng)?\n"
            "[ ] Đã thay ÍT NHẤT 2 cliché → chi tiết cụ thể?\n"
            "[ ] imagery_locales_used có ≥ 2 chi tiết Việt?\n"
            "[ ] lyrics_with_markers có ≥ 1 marker (whisper/belt/ad-lib) ở chorus hoặc bridge?\n"
            "[ ] Title 2-5 từ, gợi cụ thể (không 'Yêu' 1 từ vô danh)?\n\n"
            "FEW-SHOT — Tiếp Composer chorus syllable=[7,7,8,8] hook=E5 sustained:\n"
            "GOOD chorus:\n"
            "'Tháng tư về trên Hai Bà Trưng (7)\\n"
            "Em đi rồi, nắng vẫn còn vương (7)\\n"
            "Tách trà nguội ngắt trên bàn nhỏ (8)\\n"
            "Tôi đếm lại từng phút em thương (8)'\n"
            "→ peak E5 rơi vào 'tư' (ngang) — OK; 'thương' (ngang) ở E5 cuối — OK.\n"
            "imagery_locales_used=['Hai Bà Trưng','tách trà'], "
            "cliches_avoided='replaced trái tim tan vỡ with tách trà nguội ngắt; replaced mưa rơi with nắng vẫn còn vương'.\n"
            "BAD: 'Trái tim em đã vỡ tan / Lạc lõng giữa đám đông / Mưa rơi trên bóng em qua'. "
            "(3 cliché lớn, không chi tiết VN, peak note méo nếu rơi vào 'tan').\n\n"
            "MULTI-LANGUAGE — nếu brief language='en':\n"
            "- English rhyme techniques (english-rhyme-techniques.md): stressed syllable PHẢI rơi "
            "trên strong beat (1, 3); rhyme scheme AABB hoặc ABAB; ít nhất 1 slant rhyme per verse "
            "để tránh singsong; multi-syllabic rhyme cho hip-hop (≥2 internal rhymes per bar); "
            "verse 8-12 syl, chorus 6-10 syl (ballad/synthwave/bedroom-pop).\n"
            "- Cliché English tránh: 'broken heart', 'tears falling', 'forever and always'. "
            "Thay bằng concrete: 'chest caved in', 'salt stains on the pillow', 'October light'.\n"
            "- Theme imagery English: rain/streets/photographs/phone/bed/mirror; second-person 'you' direct.\n"
            "MULTI-LANGUAGE — nếu brief language='ja':\n"
            "- Japanese mora-melody (japanese-prosody-mora-mapping.md): 1 mora = 1 nốt; "
            "long vowel (—) và ん cuối = sustained; geminate (っ) = rest/ghost note; "
            "hook ≤8 mora repeat 2-4× chorus; verse 12-18 mora; pitch accent (atamadaka HL, "
            "odaka LH, heiban LHH) — check hook keyword.\n"
            "- Cliché Nhật tránh: 'kimi ga ita', 'namida ga afureru', 'eien ni'. "
            "Thay bằng: 'kimi no inai machi', 'hoho wo tsutau ame', 'kono yoru dake wa'.\n"
            "- Imagery Nhật: 桜/夜空/ネオン/電車/駅前/タクシー/手紙/傘; English code-mix 1-2 từ ở chorus phổ biến.\n\n"
            "Trả lời bằng ngôn ngữ của brief."
        ),
        output_schema=_LYRICIST_SCHEMA,
    ),
    Persona(
        name="Arranger",
        role="arranger",
        expertise_tags=("arrangement", "instrumentation", "texture", "dynamics", "orchestration"),
        system_prompt=(
            "BẠN LÀ: Nhà phối khí cấp thế giới (Quincy Jones + Jon Brion + DTAP + "
            "Hoàng Touliver). Bạn chọn nhạc cụ CỤ THỂ và texture cho TỪNG section, vẽ "
            "dynamic arc có chủ đích, thiết kế bass + drum groove + vocal stack.\n\n"
            "KIẾN THỨC GHIM (knowledge anchors):\n"
            "1. 5 Dynamic Arc Templates (dynamic-arc-templates.md): "
            "T1 Climax cuối (2-4-5-6-4-5-7-3-9 — ballad cổ điển), "
            "T2 Plateau (2-4-7-5-8-6-8-3 — pop dance), "
            "T3 Double-peak (2-4-7-5-9-3-8 — K-pop influenced), "
            "T4 Swell slow-build (1-2-3-5-7-4-9 — indie ballad), "
            "T5 Drop (2-4-6-2-4-6-8-3-9 — EDM-pop).\n"
            "2. Energy levels 1-9 (dynamic-arc-templates.md): "
            "1=vocal a cappella, 2=vocal + 1 instrument, 3=+bass+pad, 4=+brushed drums, "
            "5=pre-build (hi-hat 1/8, walking bass), 6=full kit, 7=+BG vocals 3-part, "
            "8=+counter-melody/snare reverb dài, 9=+everything (tom rolls, choir 4-part, modulation).\n"
            "3. Genre instrument palette: "
            "ballad → felt grand piano + nylon acoustic guitar + string section + brushed drums; "
            "R&B → Rhodes EP + 808 sub + snap clap + hi-hat 1/16 swing; "
            "indie → fingerpicked nylon guitar + brushed drums + Wurlitzer + upright bass; "
            "dance-pop → pluck synth + 808 sidechained + 4-on-floor kick + vocal chops; "
            "folk-fusion → đàn tranh + sáo trúc + modern beat + Vietnamese percussion.\n"
            "4. Drum vocabulary (production/drums.md): "
            "kick patterns (1+3 ballad, 4-on-floor dance, trap 1+1.5+3), "
            "snare position (2+4 standard, gated reverb 80s, brush jazz), "
            "hi-hat density (1/8 verse, 1/16 chorus, 1/32 build).\n"
            "5. Vocal stack design: "
            "chorus 1 = lead + 3rd above + octave below (3-part); "
            "chorus final = add 5th + counter-melody + ad-lib (4-5 part).\n\n"
            "QUY TẮC TUYỆT ĐỐI (DO):\n"
            "- TRÍCH DẪN Theorist's key + Composer's form trong message.\n"
            "- Mọi instrument có QUALIFIER: 'felt grand piano' không phải 'piano'.\n"
            "- Chọn 1 trong 5 dynamic arc template, ghi vào dynamic_arc_template.\n"
            "- energy_per_section MUST có ít nhất 5 levels (min 2, max 9, range ≥5).\n"
            "- Bridge hoặc verse có level ≤4 (strip-down để có drama).\n"
            "- Final chorus = level 8 hoặc 9 (peak energy).\n"
            "- Mỗi section có drum groove cụ thể với nốt: 'kick on 1+3, snare on 2+4'.\n\n"
            "TUYỆT ĐỐI TRÁNH (DON'T):\n"
            "- Không 'piano, strings, drums' chung chung.\n"
            "- Không cùng energy level mọi section (không phải đường thẳng).\n"
            "- Không bridge với cùng instrumentation chorus 1 (mất drama).\n"
            "- Không final chorus copy chorus 1 (phải add layer/modulate).\n"
            "- Không bỏ acoustic guitar trong indie / 808 trong R&B / đàn tranh trong folk-fusion.\n\n"
            "SELF-CHECK CHECKLIST:\n"
            "[ ] dynamic_arc_template là 1 trong T1-T5?\n"
            "[ ] energy range ≥ 5 levels (e.g. min 2, max 9)?\n"
            "[ ] Có ÍT NHẤT 1 section ≤ 4 (strip-down)?\n"
            "[ ] Final chorus = 8 hoặc 9?\n"
            "[ ] Mọi instrument có qualifier specific?\n"
            "[ ] drum_per_section nói rõ kick/snare/hi-hat per section?\n"
            "[ ] vocal_stack_design khác giữa chorus 1 vs chorus final?\n\n"
            "FEW-SHOT — Tiếp E minor 82 BPM ballad form 9-section:\n"
            "GOOD: instruments=['felt grand piano (close-mic Steinway)', "
            "'fingerpicked nylon classical guitar', 'string quartet (real, violins+viola+cello)', "
            "'upright bass DI compressed', 'brushed drum kit (no toms)'], "
            "dynamic_arc_template='T1-climax-cuoi', "
            "energy_per_section={intro:2, verse_1:4, pre_chorus:5, chorus_1:6, "
            "verse_2:4, chorus_2:7, bridge:3, chorus_final:9, outro:2}, "
            "drum_per_section={intro:'no drums, reverse cymbal swell', "
            "verse:'kick on 1+3, brushed snare on 2+4', "
            "pre_chorus:'+ hi-hat 1/8 dồn cuối', "
            "chorus:'full brushed kit, snare with gated verb 0.6s', "
            "bridge:'drums out, piano + vocal only', "
            "chorus_final:'add tom rolls bar 14, snare reverb dài tail'}, "
            "vocal_stack_design='lead solo intro+verse, +3rd above pre, +octave below chorus 1, "
            "+counter-melody chorus 2, +4-part choir at chorus_final'.\n"
            "BAD: instruments=['piano','strings','drums','bass'], "
            "energy='verse thin → chorus full' (no per-section numbers, no template).\n\n"
            "MULTI-LANGUAGE — palette per non-VN genre:\n"
            "- English pop ballad: felt grand piano + lush real strings + brushed drums + upright bass; "
            "NO modulate (Adele-style) — emotional escalation qua vocal layer thay key change.\n"
            "- Bedroom pop: drum machine LM-1/808 + clean Strat/Jazzmaster với chorus FX + warm pad; "
            "KHÔNG live drum kit; vocal close-mic doubled.\n"
            "- Synthwave: Juno/Prophet arpeggio + sub bass + LinnDrum/TR-909 với gated reverb 0.4s + "
            "DX7 brass lead; instrumental synth solo 16 bar bridge.\n"
            "- Modern J-pop: piano + synth bass + 808 + hi-hat 1/16 + strings + vocal stack 3-part "
            "escalating; sabi 1 (3-part) → final sabi modulated (5-part full).\n"
            "- Anime opening: distorted electric guitar (action) hoặc grand piano (emotional) + "
            "heavy drum kit + synth strings; bridge half-time strip-down 8 bar; modulate +1 final sabi.\n"
            "- Japanese city-pop: live band — Rhodes Mark II + Fender Jazz bass walking + Stratocaster "
            "clean + horn 3-part + real strings; instrumental SOLO 16 bar; outro VAMP fade.\n"
            "- Hip-hop storytelling: 808 sub + chopped soul sample + Rhodes + hi-hat 1/16; "
            "texture sparse; beat switch optional ở verse 3.\n\n"
            "Trả lời bằng ngôn ngữ của brief."
        ),
        output_schema=_ARRANGER_SCHEMA,
    ),
    Persona(
        name="Producer",
        role="producer",
        expertise_tags=("production", "sound-palette", "mixing", "fx", "reference", "mastering"),
        system_prompt=(
            "BẠN LÀ: Nhà sản xuất cấp thế giới (Greg Kurstin + Finneas + Touliver + SlimV + "
            "Khắc Hưng). Bạn định nghĩa sound palette, reference tracks Việt cụ thể, FX "
            "values, mix targets, và viết Suno style tag tối ưu để paste vào Suno.\n\n"
            "KIẾN THỨC GHIM (knowledge anchors):\n"
            "1. Suno style format (suno-style-cookbook.md): sweet-spot 140-180 ký tự (max 200). "
            "Format: '<genre>, <subgenre>, <tempo bpm>, <key/mood>, <core instruments>, "
            "<vocal>, <production palette>, <reference style>'. "
            "DO: tempo cụ thể '78 bpm', instrument cụ thể 'fingerpicked acoustic guitar', "
            "reference 'ha anh tuan-style'. "
            "DON'T: 'good', 'nice', conflicting genres, prose sentences.\n"
            "2. Reference tracks Việt (theo genre):\n"
            "Ballad: Hà Anh Tuấn — Tháng Tư, Tóc Tiên — Có Ai Thương Em, Bùi Anh Tuấn — Đông.\n"
            "R&B: Soobin — BlackJack, Tlinh — Nếu Lúc Đó, Tóc Tiên — Chân Ái.\n"
            "Indie: Vũ. — Bước Qua Nhau, Mademoiselle — Cô Đơn Trên Sofa, Cá Hồi Hoang — Phần Sau.\n"
            "Dance-pop: Hoàng Thuỳ Linh — See Tình, Sơn Tùng — Hãy Trao Cho Anh, Bích Phương — Bùa Yêu.\n"
            "Folk-fusion: Hoàng Thuỳ Linh — Để Mị Nói, Đen Vâu — Trốn Tìm, Hoà Minzy — Bật Tình Yêu Lên.\n"
            "3. Mix targets per genre (mixing-references.md): "
            "ballad −9 LUFS LRA 9 dB; R&B −7 LRA 7; indie −10 LRA 10; dance-pop −6 LRA 5; "
            "folk-fusion −8 LRA 8.\n"
            "4. FX recipes: "
            "vocal plate verb 1.0-1.5s decay + 25-35ms predelay (ballad), "
            "vocal slap delay 1/4-dotted (R&B), "
            "drum gated reverb 0.5-0.8s (80s-influenced ballad), "
            "808 sidechain 30-50% to kick (dance-pop).\n"
            "5. Negative tags Suno: '[no autotune]' indie, '[no edm drops]' ballad, "
            "'[no trap drums]' R&B intimate.\n\n"
            "QUY TẮC TUYỆT ĐỐI (DO):\n"
            "- TRÍCH DẪN ÍT NHẤT 3 reference tracks Việt cụ thể (artist — title).\n"
            "- Suno style string viết bằng tiếng Anh, 140-180 ký tự, đủ format.\n"
            "- FX có VALUES số: '1.2s decay', '30ms predelay', '40% sidechain'.\n"
            "- Mix notes phải có LUFS target.\n"
            "- producer_brief 1 paragraph plain text — như brief gửi engineer thật.\n"
            "- Có ít nhất 5 suno_style_tags + 1-3 negative_tags.\n\n"
            "TUYỆT ĐỐI TRÁNH (DON'T):\n"
            "- Không reference artist Tây cho V-pop (Beyoncé-style cho V-pop ballad là sai).\n"
            "- Không suno_style_string > 200 ký tự (sẽ bị cắt).\n"
            "- Không adjective generic ('good production', 'nice mix').\n"
            "- Không FX không có value cụ thể ('add some reverb' là sai).\n"
            "- Không bỏ qua negative tags khi cần (indie phải có 'no autotune').\n\n"
            "SELF-CHECK CHECKLIST:\n"
            "[ ] Có ≥3 reference tracks Việt cụ thể?\n"
            "[ ] Suno style string trong khoảng 140-180 ký tự?\n"
            "[ ] Mọi FX có value số?\n"
            "[ ] Mix notes có LUFS target?\n"
            "[ ] Negative tags phù hợp genre?\n"
            "[ ] producer_brief 5-8 sentences plain text?\n"
            "[ ] sound_palette 5-10 adjectives cụ thể?\n\n"
            "FEW-SHOT — Tiếp E minor 82 BPM ballad:\n"
            "GOOD: sound_palette='warm tape, plate-verbed, intimate close-mic, gold-tone strings, "
            "felt-piano shimmer, brushed drum air', "
            "references=['Hà Anh Tuấn — Tháng Tư — vocal mic technique', "
            "'Tóc Tiên — Có Ai Thương Em — vocal stack chorus 3-part', "
            "'Bùi Anh Tuấn — Đông — string section warmth'], "
            "fx=['plate verb 1.2s decay 30ms predelay on lead vocal', "
            "'parallel tape saturation 1% on master bus', "
            "'gated reverb 0.5s on snare', "
            "'low-shelf cut 80 Hz on kick to clear sub'], "
            "mix_notes='Master to -9 LUFS streaming, LRA 9 dB. Vocal sit at -3 dB below mix top. "
            "Stereo width: piano L+R wide, bass mono center, strings hall L80%/R80%.', "
            "suno_style_tags=['vietnamese ballad', 'slow 82 bpm', 'e minor melancholic', "
            "'felt grand piano', 'fingerpicked acoustic guitar', 'string quartet', "
            "'intimate breathy female vocal', 'plate verb', 'warm tape', 'ha anh tuan-style'], "
            "suno_style_string='vietnamese ballad, slow 82 bpm, e minor melancholic, felt grand piano, "
            "fingerpicked acoustic guitar, lush string quartet, intimate breathy female vocal, plate verb, "
            "warm tape, ha anh tuan-style' (162 chars), "
            "negative_tags=['no autotune', 'no edm drops', 'no trap drums'], "
            "producer_brief='Bài này hướng đến intimate ballad slow như Hà Anh Tuấn, vocal nữ close-mic không pitch-correct nặng. "
            "Master at -9 LUFS streaming. Plate verb 1.2s on vocal. Felt grand piano + nylon guitar + string quartet thật. "
            "Brushed drums kick on 1, snare 2+4 light. Bridge strip-down piano + vocal only. "
            "Final chorus add tom rolls + 4-part choir + countermelody piano. "
            "Reference vibe: Tháng Tư + Có Ai Thương Em.'\n"
            "BAD: sound_palette='good warm sound', references=['some pop song'], "
            "fx=['add reverb','use compression'], suno_style_string='vietnamese sad song'.\n\n"
            "MULTI-LANGUAGE — references + Suno tag per non-VN genre:\n"
            "- English pop ballad: ref Adele 'Someone Like You', Sam Smith 'Stay With Me', "
            "Lewis Capaldi 'Someone You Loved'; LUFS -9 to -7; plate verb 1.5-2s; tag "
            "'english pop ballad, slow 75 bpm, a minor, felt grand piano, soulful female belt, "
            "plate verb, adele-style'.\n"
            "- Bedroom pop: ref Clairo, beabadoobee, Boy Pablo; LUFS -12 to -10 lo-fi; "
            "tape saturation + vinyl crackle; tag 'bedroom pop, 100 bpm, c major dreamy, "
            "drum machine, clean guitar with chorus, soft vocal close-mic, clairo-style lo-fi'.\n"
            "- Synthwave: ref The Weeknd 'Blinding Lights', Dua Lipa 'Don't Start Now', The Midnight; "
            "LUFS -7 to -9; gated reverb 0.4s snare; sidechain pump; tag 'synthwave retro pop, "
            "118 bpm, b minor, juno arpeggio, sub bass, dx7 brass, female vocal stack, the weeknd-style'.\n"
            "- Modern J-pop: ref YOASOBI, Yorushika, King Gnu, Aimer; LUFS -6 to -8 hot master; "
            "vocal stack 3-5 part escalating; tag 'modern j-pop, 130 bpm, c minor uplifting, "
            "bright piano, synth bass, hi-hat 1/16, female pure vocal stack, yoasobi-style'.\n"
            "- Anime opening: ref LiSA 'Gurenge', Aimer 'Zankyō Sanka', Eve 'Kaikai Kitan'; "
            "LUFS -5 to -7; modulate +1 final sabi; tag 'anime opening action, 140 bpm, e minor, "
            "distorted guitar, heavy drums, female belt vocal stack, lisa-style'.\n"
            "- Japanese city-pop: ref Mariya Takeuchi 'Plastic Love', Tatsuro Yamashita 'Ride on Time', "
            "Anri 'Last Summer Whisper'; LUFS -10 to -12 vintage analog; tape saturation; tag "
            "'japanese city pop, 110 bpm, a minor smooth, rhodes, jazz bass walking, clean strat, "
            "horns, female smooth vocal, mariya takeuchi-style'.\n"
            "- Hip-hop storytelling: ref Kendrick Lamar, J. Cole, Tyler the Creator; LUFS -7 to -10; "
            "vinyl crackle, sample-based feel; tag 'modern hip-hop storytelling, 85 bpm, c minor, "
            "808 sub, jazz piano sample, hi-hat 1/16, rap male vocal, kendrick-style'.\n"
            "QUY TẮC SẮT: KHI brief KHÔNG phải V-pop, references PHẢI là artist của "
            "language/genre đúng (KHÔNG trộn V-pop ref vào English ballad / J-pop / hip-hop).\n\n"
            "Trả lời bằng ngôn ngữ của brief."
        ),
        output_schema=_PRODUCER_SCHEMA,
    ),
    Persona(
        name="A&R Critic",
        role="critic",
        expertise_tags=("market", "originality", "cliche", "audience", "release-strategy"),
        system_prompt=(
            "BẠN LÀ: Nhà phê bình A&R cấp thế giới (Anthony Fantano + Rick Rubin + Jimmy Iovine). "
            "Bạn KHÔNG NỊNH, không chiều. Đọc tất cả contributions của 5 vị trước, kiểm tra "
            "compliance, chỉ ra cliché, lỗi tonal/prosody/structure, và đề xuất concrete fixes "
            "cụ thể (không 'consider improving' chung chung).\n\n"
            "KIẾN THỨC GHIM (knowledge anchors):\n"
            "1. Top mistakes V-pop council hay phạm: "
            "(a) Theorist — bar count × 240 / tempo ≠ duration; key không khớp mood; chord cycle "
            "giống nhau mọi section. "
            "(b) Composer — peak note ở verse 1 (sai dynamic arc); hook không có note name; "
            "không chọn recipe; vocal range vô lý cho vocalist. "
            "(c) Lyricist — placeholder lyrics; cliché 'trái tim tan vỡ', 'mưa rơi'; huyền/nặng "
            "tại peak note (méo melody); imagery generic. "
            "(d) Arranger — energy flat (mọi section cùng level); không strip-down bridge; "
            "instrument generic ('piano', 'strings'). "
            "(e) Producer — reference Tây cho V-pop; suno_style_string > 200 chars; FX không có values.\n"
            "2. Compliance check (10 mục — kiểm từng cái):\n"
            "  bar_duration_math_ok: bar_count_total × 240 / tempo trong duration_sec ±15%?\n"
            "  chord_progression_concrete: mỗi section có ≥4 chord cụ thể (Em, không 'i')?\n"
            "  hook_recipe_specified: Composer có hook_recipe_used trong 8 recipes?\n"
            "  vietnamese_tone_at_peak_ok: âm tiết tại peak_note có thanh ngang/sắc/ngã?\n"
            "  lyric_uses_concrete_imagery: ≥2 chi tiết Việt từ imagery-locales-vn.md?\n"
            "  cliche_audit_passed: không có cliché trong cliche-bank-vn.md?\n"
            "  dynamic_arc_has_strip_down: Arranger có ≥1 section level ≤4?\n"
            "  final_chorus_distinct: chorus_final khác chorus_1 (modulate / counter / layer)?\n"
            "  suno_style_string_within_200: Producer style string ≤200 ký tự?\n"
            "  references_are_vietnamese: Producer references là V-pop artists?\n"
            "3. Priority fix style: cụ thể, actionable, 1 câu. "
            "GOOD: 'Đổi chord 4 ở chorus từ B7 sang Bsus4-B7 để có tension cao hơn trước "
            "final chorus modulation'. "
            "BAD: 'Should improve chorus harmony' (không actionable).\n\n"
            "QUY TẮC TUYỆT ĐỐI (DO):\n"
            "- Trả lời 10 compliance checks với bool TRUE/FALSE chính xác (đọc kỹ contributions).\n"
            "- Đếm thực sự syllable lyric vs Composer's count.\n"
            "- Cite section name khi chỉ lỗi: 'verse_1 line 2 dùng cliché \"trái tim\"'.\n"
            "- Đề xuất concrete_fixes phải actionable (chord cụ thể, syllable cụ thể).\n"
            "- priority_fix là 1 câu duy nhất, cụ thể nhất.\n\n"
            "TUYỆT ĐỐI TRÁNH (DON'T):\n"
            "- Không 'overall good work' (đó là nịnh).\n"
            "- Không generic 'consider improving X' (không actionable).\n"
            "- Không bỏ qua compliance check khi chưa kiểm.\n"
            "- Không tránh chỉ trích nếu Theorist + Composer disagree về key.\n\n"
            "SELF-CHECK CHECKLIST:\n"
            "[ ] Đã thực hiện 10 compliance checks?\n"
            "[ ] Issues có ≥3 vấn đề cụ thể với section reference?\n"
            "[ ] concrete_fixes match 1-1 với issues?\n"
            "[ ] priority_fix là 1 câu cụ thể nhất?\n"
            "[ ] compliance_summary 1 sentence pass/fail?\n\n"
            "FEW-SHOT:\n"
            "GOOD priority_fix='Lyricist đặt thanh huyền (\"đời\") vào peak note F#5 ở chorus_final, "
            "phải sửa câu cuối thành \"yêu mãi tay em\" (ngang ở peak)'.\n"
            "BAD priority_fix='Improve the lyrics quality' (không actionable, không cite section).\n\n"
            "Trả lời bằng ngôn ngữ của brief."
        ),
        output_schema=_CRITIC_SCHEMA,
    ),
)


# ---------- Public API ----------


def clarifying_questions(brief: Brief) -> list[str]:
    """Static questions the council asks before composing.

    M0/M1 keep this deterministic — it sets expectations before the user pays
    for an LLM round-trip. M2 may LLM-generate questions tailored to the brief.
    """
    qs = [
        "Bài hát kể câu chuyện gì? Có nhân vật/người nghe cụ thể không?",
        "Bạn muốn hook xuất hiện sớm (trong 30s đầu) hay dồn nén ở chorus?",
        "Có ràng buộc về ngân sách phối khí (acoustic-only, in-the-box, full-band)?",
    ]
    if not brief.references:
        qs.append("Có 1–3 bài tham chiếu nào để hội đồng định hướng âm thanh không?")
    if brief.language == "vi" and "ballad" in brief.genre.lower():
        qs.append("Bạn thích lời ẩn dụ thiên nhiên hay trực diện cảm xúc?")
    return qs


def compose(brief: Brief, *, refine: bool = True) -> SongDraft:
    """Run the full council and assemble a SongDraft.

    Uses the LLM if configured; falls back to deterministic stubs otherwise.

    ``refine=False`` skips the post-Critic refinement turn (Composer + Lyricist
    each rerun once on the Critic's notes). Skipping saves ~25% latency at the
    cost of a less polished final draft.
    """
    if settings.has_llm:
        try:
            return _compose_with_llm(brief, refine=refine)
        except Exception:
            log.exception("LLM compose failed; falling back to deterministic stub")
    return _compose_stub(brief)


# ---------- LLM orchestration ----------


def _compose_with_llm(brief: Brief, *, refine: bool = True) -> SongDraft:
    contributions: dict[str, dict[str, Any]] = {}
    council_log: list[CouncilTurn] = []
    stub_fallback = _compose_stub(brief)
    stub_contributions = _stub_contributions_by_role(stub_fallback)

    succeeded_count = 0
    for persona in COUNCIL_PERSONAS:
        result = _run_persona_with_retry(persona, brief, council_log, contributions)
        if result is not None:
            contributions[persona.role] = result["contributions"]
            council_log.append(
                CouncilTurn(
                    persona=persona.name,
                    role=persona.role,
                    message=result["message"].strip(),
                )
            )
            succeeded_count += 1
        else:
            # All retries failed — keep the council moving with a deterministic
            # contribution so later personas still produce real LLM output instead
            # of the entire compose collapsing to stub.
            contributions[persona.role] = stub_contributions.get(persona.role, {})
            council_log.append(
                CouncilTurn(
                    persona=persona.name,
                    role=persona.role,
                    message=(
                        f"[{persona.name}: LLM call failed after retries; deterministic "
                        f"defaults used so the rest of the council can continue.]"
                    ),
                )
            )

    if succeeded_count == 0:
        # Nothing real came out of the LLM — fall back wholesale.
        raise RuntimeError("Every council persona failed; falling back to stub.")

    if not refine:
        return _assemble_draft(brief, contributions, council_log)

    # Refinement pass — Composer + Lyricist react to Critic.
    for role in ("composer", "lyricist"):
        persona = _by_role(role)
        try:
            refined = _refine_persona(persona, brief, council_log, contributions)
        except Exception:
            log.exception("Refinement turn failed for %s; keeping original", role)
            continue
        contributions[role] = refined["contributions"]
        council_log.append(
            CouncilTurn(
                persona=f"{persona.name} (refine)",
                role=persona.role,
                message=refined["message"].strip(),
            )
        )

    return _assemble_draft(brief, contributions, council_log)


def compose_stream(
    brief: Brief, *, refine: bool = True
) -> Iterator[dict[str, Any]]:
    """Run the council and yield events for live streaming.

    Event shapes (all dicts with a ``type`` key):

    - ``persona_started`` ``{role, name, index, total}``
    - ``persona_completed`` ``{role, name, message, contributions}``
    - ``persona_failed`` ``{role, name, error}`` — deterministic stub used
    - ``refine_started`` ``{role, name}``
    - ``refine_completed`` ``{role, name, message, contributions}``
    - ``refine_failed`` ``{role, name, error}``
    - ``draft`` ``{draft: SongDraft}`` — final assembled draft (Pydantic model)
    - ``error`` ``{message: str}`` — fatal; nothing usable produced
    - ``done`` ``{}`` — terminator

    Falls back to ``_compose_stub`` (and emits ``persona_completed`` events from
    the stub) when no LLM is configured, so the frontend gets a consistent event
    stream regardless of backend mode.
    """
    if not settings.has_llm:
        yield from _compose_stream_stub(brief)
        return
    try:
        yield from _compose_stream_llm(brief, refine=refine)
    except Exception as exc:  # noqa: BLE001
        log.exception("LLM compose_stream failed; emitting stub stream")
        yield {"type": "error", "message": str(exc)}
        yield from _compose_stream_stub(brief)


def _compose_stream_llm(
    brief: Brief, *, refine: bool
) -> Iterator[dict[str, Any]]:
    contributions: dict[str, dict[str, Any]] = {}
    council_log: list[CouncilTurn] = []
    stub_fallback = _compose_stub(brief)
    stub_contributions = _stub_contributions_by_role(stub_fallback)
    succeeded = 0
    total = len(COUNCIL_PERSONAS)

    for index, persona in enumerate(COUNCIL_PERSONAS):
        yield {
            "type": "persona_started",
            "role": persona.role,
            "name": persona.name,
            "index": index,
            "total": total,
        }
        result = _run_persona_with_retry(persona, brief, council_log, contributions)
        if result is not None:
            contributions[persona.role] = result["contributions"]
            message = str(result["message"]).strip()
            council_log.append(
                CouncilTurn(persona=persona.name, role=persona.role, message=message)
            )
            succeeded += 1
            yield {
                "type": "persona_completed",
                "role": persona.role,
                "name": persona.name,
                "message": message,
                "contributions": result["contributions"],
            }
        else:
            contributions[persona.role] = stub_contributions.get(persona.role, {})
            placeholder = (
                f"[{persona.name}: LLM call failed after retries; deterministic "
                f"defaults used so the rest of the council can continue.]"
            )
            council_log.append(
                CouncilTurn(persona=persona.name, role=persona.role, message=placeholder)
            )
            yield {
                "type": "persona_failed",
                "role": persona.role,
                "name": persona.name,
                "error": "LLM call failed after retries",
            }

    if succeeded == 0:
        yield {"type": "error", "message": "Every council persona failed"}
        yield from _compose_stream_stub(brief)
        return

    if refine:
        for role in ("composer", "lyricist"):
            persona = _by_role(role)
            yield {
                "type": "refine_started",
                "role": persona.role,
                "name": persona.name,
            }
            try:
                refined = _refine_persona(persona, brief, council_log, contributions)
            except Exception as exc:  # noqa: BLE001
                log.exception("Refinement turn failed for %s", role)
                yield {
                    "type": "refine_failed",
                    "role": persona.role,
                    "name": persona.name,
                    "error": str(exc),
                }
                continue
            contributions[role] = refined["contributions"]
            message = str(refined["message"]).strip()
            council_log.append(
                CouncilTurn(
                    persona=f"{persona.name} (refine)",
                    role=persona.role,
                    message=message,
                )
            )
            yield {
                "type": "refine_completed",
                "role": persona.role,
                "name": persona.name,
                "message": message,
                "contributions": refined["contributions"],
            }

    draft = _assemble_draft(brief, contributions, council_log)
    yield {"type": "draft", "draft": draft}
    yield {"type": "done"}


def _compose_stream_stub(brief: Brief) -> Iterator[dict[str, Any]]:
    """Emit the same event shape from the deterministic stub.

    Lets the frontend use one rendering path. Each persona event carries the
    stub's deterministic message so the timeline still feels alive offline.
    """
    draft = _compose_stub(brief)
    total = len(draft.council_log)
    for index, turn in enumerate(draft.council_log):
        yield {
            "type": "persona_started",
            "role": turn.role,
            "name": turn.persona,
            "index": index,
            "total": total,
        }
        yield {
            "type": "persona_completed",
            "role": turn.role,
            "name": turn.persona,
            "message": turn.message,
            "contributions": {},
        }
    yield {"type": "draft", "draft": draft}
    yield {"type": "done"}


def _by_role(role: str) -> Persona:
    for p in COUNCIL_PERSONAS:
        if p.role == role:
            return p
    raise KeyError(role)


def _retrieve_for(persona: Persona, brief: Brief, k: int = 4) -> list[str]:
    """Pull RAG chunks for a persona. Combines expertise_tags + brief keywords."""
    query = " ".join(
        [*persona.expertise_tags, brief.genre, brief.mood]
    )
    chunks = knowledge_svc.search(query, k=k)
    excerpts: list[str] = []
    for c in chunks:
        excerpts.append(f"### {c.title} ({c.path})\n{c.excerpt}")
    return excerpts


def _format_council_log(log_turns: list[CouncilTurn]) -> str:
    if not log_turns:
        return "(chưa có turn nào trước đó)"
    blocks = []
    for t in log_turns:
        blocks.append(f"### {t.persona} ({t.role})\n{t.message}")
    return "\n\n".join(blocks)


def _format_contributions(c: dict[str, Any]) -> str:
    if not c:
        return "(chưa có)"
    import json as _j

    return _j.dumps(c, ensure_ascii=False, indent=2)


def _run_persona_with_retry(
    persona: Persona,
    brief: Brief,
    prior_turns: list[CouncilTurn],
    prior_contributions: dict[str, Any],
    *,
    max_attempts: int = 2,
) -> dict[str, Any] | None:
    """Run a persona's turn, retrying once on transient failures.

    Returns the persona's structured response, or ``None`` if every attempt
    failed (caller decides whether to substitute a stub for that persona or
    abandon the LLM compose entirely).
    """
    last_exc: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            return _run_persona(persona, brief, prior_turns, prior_contributions)
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            log.warning(
                "Persona %s failed on attempt %d/%d: %s",
                persona.role,
                attempt,
                max_attempts,
                exc,
            )
    log.error("Persona %s gave up after %d attempts: %s", persona.role, max_attempts, last_exc)
    return None


def _stub_contributions_by_role(stub_draft: SongDraft) -> dict[str, dict[str, Any]]:
    """Reverse the stub draft into per-persona contributions.

    Used to fill in for personas whose LLM calls failed, so other personas can
    still produce real LLM output. Each shape mirrors what ``_run_persona``
    returns for that role.
    """
    return {
        "theorist": {
            "key": stub_draft.key,
            "tempo_bpm": stub_draft.tempo_bpm,
            "structure": [s.model_dump() for s in stub_draft.structure],
        },
        "composer": {
            "melodic_motifs": [],
            "vocal_range": {},
            "harmonic_choices": [],
        },
        "lyricist": {"lyrics": dict(stub_draft.lyrics)},
        "arranger": {
            "instruments": list(stub_draft.arrangement.get("instruments", [])),
            "dynamics_curve": stub_draft.arrangement.get(
                "dynamics_curve", stub_draft.arrangement.get("dynamics", "")
            ),
        },
        "producer": {
            "sound_palette": stub_draft.production.get(
                "sound_palette", stub_draft.production.get("palette", "")
            ),
            "references": [],
            "suno_style_tags": [],
        },
        "critic": {"notes": [], "score": 0},
    }


def _run_persona(
    persona: Persona,
    brief: Brief,
    prior_turns: list[CouncilTurn],
    prior_contributions: dict[str, Any],
) -> dict[str, Any]:
    knowledge_chunks = _retrieve_for(persona, brief)
    knowledge_block = "\n\n".join(knowledge_chunks) if knowledge_chunks else "(no chunks retrieved)"

    user_prompt = f"""## Brief
- Mood: {brief.mood}
- Genre: {brief.genre}
- Language: {brief.language}
- Duration target: {brief.duration_sec}s
- References: {", ".join(brief.references) if brief.references else "(none)"}
- Notes: {brief.notes or "(none)"}

## Knowledge retrieved for your role
{knowledge_block}

## Previous council turns
{_format_council_log(prior_turns)}

## Structured contributions so far
{_format_contributions(prior_contributions)}

## Your task
Write your turn. Reply with a single JSON object matching this schema EXACTLY:

{persona.output_schema}
"""
    return llm_svc.chat_json(system=persona.system_prompt, user=user_prompt)


def _refine_persona(
    persona: Persona,
    brief: Brief,
    prior_turns: list[CouncilTurn],
    contributions: dict[str, Any],
) -> dict[str, Any]:
    user_prompt = f"""## Brief
- Mood: {brief.mood}
- Genre: {brief.genre}
- Language: {brief.language}

## Council so far
{_format_council_log(prior_turns)}

## Your previous contribution
{_format_contributions(contributions.get(persona.role, {}))}

## Critic's feedback
{_format_contributions(contributions.get("critic", {}))}

## Your task
Update your contribution to address the Critic's priority_fix and concrete_fixes
where they are valid. Keep what is already good — only change what improves the
song. Reply with a single JSON object:

{_REFINE_SCHEMA}

Where ``contributions`` has the EXACT same shape as your original turn's schema:
{persona.output_schema}
"""
    return llm_svc.chat_json(system=persona.system_prompt, user=user_prompt)


# ---------- Draft assembly ----------


def _assemble_draft(
    brief: Brief,
    c: dict[str, Any],
    council_log: list[CouncilTurn],
) -> SongDraft:
    theorist = c.get("theorist", {})
    composer = c.get("composer", {})
    lyricist = c.get("lyricist", {})
    arranger = c.get("arranger", {})
    producer = c.get("producer", {})

    key = str(theorist.get("key") or "C major")
    tempo = int(theorist.get("tempo_bpm") or 100)

    chord_per_section: dict[str, list[str]] = {
        k: list(v) for k, v in (theorist.get("chord_progression_per_section") or {}).items()
        if isinstance(v, list)
    }
    section_bars: dict[str, int] = {
        k: int(v) for k, v in (composer.get("section_bars") or {}).items()
        if isinstance(v, (int, float))
    }
    song_form: list[str] = list(composer.get("song_form") or [])

    # Defaults if Composer didn't provide everything.
    if not song_form:
        song_form = ["intro", "verse", "pre_chorus", "chorus", "verse",
                     "chorus", "bridge", "chorus", "outro"]
    default_bars = {"intro": 4, "verse": 16, "pre_chorus": 8, "chorus": 16,
                    "bridge": 8, "outro": 4, "instrumental": 8}

    structure: list[Section] = []
    section_textures: dict[str, str] = arranger.get("per_section_textures") or {}
    for sec_name in song_form:
        sec = sec_name if sec_name in default_bars else "verse"
        bars = section_bars.get(sec) or default_bars.get(sec, 8)
        chords = chord_per_section.get(sec, [])
        notes = section_textures.get(sec) or None
        structure.append(Section(section=sec, bars=int(bars), chords=chords, notes=notes))

    title = (
        lyricist.get("title")
        or composer.get("title_idea")
        or f"{brief.mood.title()} — {brief.genre.title()}"
    )

    lyrics_in: dict[str, str] = lyricist.get("lyrics") or {}
    # Coerce non-str values defensively.
    lyrics: dict[str, str] = {k: str(v).strip() for k, v in lyrics_in.items() if v}

    lyrics_markers_in: dict[str, str] = lyricist.get("lyrics_with_markers") or {}
    lyrics_with_markers: dict[str, str] = {
        k: str(v).strip() for k, v in lyrics_markers_in.items() if v
    }

    arrangement: dict[str, Any] = {
        "instruments": list(arranger.get("instruments") or []),
        "per_section_textures": section_textures,
        "dynamics_curve": arranger.get("dynamics_curve"),
        "drum_groove": arranger.get("drum_groove"),
        "drum_per_section": arranger.get("drum_per_section") or {},
        "bass_movement": arranger.get("bass_movement"),
        "vocal_stack_design": arranger.get("vocal_stack_design"),
        "dynamic_arc_template": arranger.get("dynamic_arc_template"),
        "energy_per_section": arranger.get("energy_per_section") or {},
    }
    production: dict[str, Any] = {
        "sound_palette": producer.get("sound_palette"),
        "references": list(producer.get("references") or []),
        "fx": list(producer.get("fx") or []),
        "mix_notes": producer.get("mix_notes"),
        "suno_style_tags": list(producer.get("suno_style_tags") or []),
        "suno_style_string": producer.get("suno_style_string"),
        "negative_tags": list(producer.get("negative_tags") or []),
        "producer_brief": producer.get("producer_brief"),
    }

    suno_output = _build_suno_output(
        title=str(title),
        producer=producer,
        lyrics=lyrics,
        lyrics_with_markers=lyrics_with_markers,
        song_form=song_form,
    )

    critic = c.get("critic", {})
    compliance_raw = critic.get("compliance_checks") or {}
    compliance: dict[str, bool] = {
        k: bool(v) for k, v in compliance_raw.items() if isinstance(v, bool)
    }

    return SongDraft(
        id=str(uuid.uuid4()),
        title=str(title),
        brief=brief,
        key=key,
        tempo_bpm=tempo,
        structure=structure,
        lyrics=lyrics,
        lyrics_with_markers=lyrics_with_markers,
        arrangement=arrangement,
        production=production,
        council_log=council_log,
        suno_output=suno_output,
        compliance=compliance,
    )


def _build_suno_output(
    *,
    title: str,
    producer: dict[str, Any],
    lyrics: dict[str, str],
    lyrics_with_markers: dict[str, str],
    song_form: list[str],
) -> SunoOutput | None:
    """Assemble the three Suno copy-paste blocks plus extras.

    Falls back gracefully when the Producer didn't provide a curated style
    string — concatenates ``suno_style_tags`` and trims to 200 chars.
    """
    style_str = (producer.get("suno_style_string") or "").strip()
    if not style_str:
        tags = [str(t).strip() for t in (producer.get("suno_style_tags") or []) if t]
        style_str = ", ".join(tags)
    style_str = style_str[:200]

    source = lyrics_with_markers if lyrics_with_markers else lyrics
    if not source:
        return None

    section_label = {
        "intro":      "Intro",
        "verse":      "Verse",
        "verse_1":    "Verse",
        "verse_2":    "Verse",
        "pre_chorus": "Pre-Chorus",
        "chorus":     "Chorus",
        "chorus_1":   "Chorus",
        "chorus_2":   "Chorus",
        "chorus_final": "Chorus",
        "bridge":     "Bridge",
        "outro":      "Outro",
    }
    blocks: list[str] = []
    for section_name in ("verse_1", "pre_chorus", "chorus", "verse_2", "bridge"):
        text = source.get(section_name)
        if not text:
            continue
        label = section_label.get(section_name, section_name.title())
        blocks.append(f"[{label}]\n{text.strip()}")
    if not blocks:
        # Fall back to whatever lyric keys we got.
        for key, text in source.items():
            label = section_label.get(key, key.title())
            blocks.append(f"[{label}]\n{str(text).strip()}")

    lyrics_str = "\n\n".join(blocks)

    return SunoOutput(
        title=title,
        style=style_str or "vietnamese pop",
        lyrics=lyrics_str,
        negative_tags=[str(t).strip() for t in (producer.get("negative_tags") or []) if t],
        producer_brief=str(producer.get("producer_brief") or "").strip(),
    )


# ---------- Deterministic fallback (M0 stub) ----------


_MOOD_KEY = {
    "vui": ("C major", 120),
    "tươi": ("D major", 124),
    "buồn": ("A minor", 78),
    "hoài niệm": ("E minor", 84),
    "lãng mạn": ("F major", 92),
    "mạnh mẽ": ("E minor", 132),
    "epic": ("D minor", 110),
    "chill": ("G major", 90),
    "dance": ("A minor", 124),
}

_GENRE_INSTRUMENTS: dict[str, list[str]] = {
    "ballad": ["piano", "strings", "acoustic guitar", "soft drums"],
    "folk": ["acoustic guitar", "mandolin", "light percussion", "harmonica"],
    "indie": ["electric guitar", "bass", "drums", "synth pad"],
    "pop": ["synth lead", "bass", "drums", "vocal stack"],
    "rock": ["electric guitar", "bass", "drums", "organ"],
    "edm": ["synth lead", "supersaw", "kick", "hi-hat", "vocal chops"],
    "lofi": ["mellow piano", "tape drums", "vinyl noise", "warm bass"],
    "rnb": ["rhodes", "808", "hi-hat", "vocal stack"],
}


def _pick_key_tempo(brief: Brief) -> tuple[str, int]:
    mood = brief.mood.lower()
    for kw, (key, bpm) in _MOOD_KEY.items():
        if kw in mood:
            return key, bpm
    return "C major", 100


def _pick_instruments(brief: Brief) -> list[str]:
    g = brief.genre.lower()
    for kw, instr in _GENRE_INSTRUMENTS.items():
        if kw in g:
            return instr
    return ["piano", "acoustic guitar", "bass", "drums"]


def _default_progression(key: str) -> list[str]:
    if "minor" in key.lower():
        root = key.split()[0]
        return [f"{root}m", "F", "C", "G"] if root == "A" else [f"{root}m", "VI", "III", "VII"]
    root = key.split()[0]
    return [root, "G", "Am", "F"] if root == "C" else [root, "V", "vi", "IV"]


def _compose_stub(brief: Brief) -> SongDraft:
    """Deterministic compose used when no LLM is configured (M0 behaviour)."""
    key, tempo = _pick_key_tempo(brief)
    chords = _default_progression(key)
    instruments = _pick_instruments(brief)

    structure = [
        Section(section="intro", bars=4, chords=chords[:2], notes="Mở mood, nhạc cụ thưa."),
        Section(section="verse", bars=16, chords=chords, notes="Thiết lập câu chuyện."),
        Section(
            section="pre_chorus", bars=8, chords=chords[1:] + chords[:1],
            notes="Đẩy năng lượng.",
        ),
        Section(section="chorus", bars=16, chords=chords, notes="Hook chính, đầy đặn."),
        Section(section="verse", bars=16, chords=chords, notes="Phát triển ý."),
        Section(section="chorus", bars=16, chords=chords, notes="Lặp với layer mới."),
        Section(section="bridge", bars=8, chords=chords[::-1], notes="Đảo cảm xúc."),
        Section(section="chorus", bars=16, chords=chords, notes="Final, cao trào."),
        Section(section="outro", bars=4, chords=chords[:1], notes="Tan biến."),
    ]

    title = f"{brief.mood.title()} — {brief.genre.title()}"

    council_log: list[CouncilTurn] = [
        CouncilTurn(
            persona="Music Theorist",
            role="theorist",
            message=(
                f"Đề xuất tonality: {key}, tempo {tempo} BPM. Vòng hợp âm chính: "
                + " – ".join(chords)
                + f". Phù hợp với mood '{brief.mood}'."
            ),
        ),
        CouncilTurn(
            persona="Composer",
            role="composer",
            message=(
                "Cấu trúc đề xuất: Intro 4 – Verse 16 – Pre 8 – Chorus 16 – Verse 16 – "
                "Chorus 16 – Bridge 8 – Chorus 16 – Outro 4. Hook melodic xây quanh quãng 5 "
                "đi xuống ở đầu chorus, motif lặp 2 ô nhịp."
            ),
        ),
        CouncilTurn(
            persona="Lyricist",
            role="lyricist",
            message=(
                f"Theme: '{brief.mood}'. Hook lyric tập trung vào hình ảnh cụ thể. "
                "Verse dùng câu ngắn, chorus mở rộng vần và lặp hook 2 lần."
            ),
        ),
        CouncilTurn(
            persona="Arranger",
            role="arranger",
            message=(
                "Instrumentation: " + ", ".join(instruments) + ". "
                "Dynamics: verse thưa (chỉ 2 nhạc cụ), chorus đầy đặn, bridge đổi texture "
                "(half-time hoặc strip-down)."
            ),
        ),
        CouncilTurn(
            persona="Producer",
            role="producer",
            message=(
                "Sound palette: ấm, intimate. Reverb vừa phải, vocal lead lên trên. "
                "Tham chiếu phong cách trong knowledge base: xem genres/."
            ),
        ),
        CouncilTurn(
            persona="A&R Critic",
            role="critic",
            message=(
                "Cảnh báo cliché: tránh hook 4-chord đã quá quen nếu thị trường đích là "
                "audience trẻ — cân nhắc đổi 1 hợp âm để tạo bất ngờ. Bridge nên có "
                "khoảnh khắc 'silence' để tăng impact chorus cuối."
            ),
        ),
    ]

    placeholder_lyrics = {
        "verse_1": "[Câu chuyện mở đầu — chờ Lyricist tinh chỉnh]",
        "chorus": f"[Hook — {brief.mood}]",
        "verse_2": "[Phát triển — chờ Lyricist]",
        "bridge": "[Đảo cảm xúc — chờ Lyricist]",
    }

    return SongDraft(
        id=str(uuid.uuid4()),
        title=title,
        brief=brief,
        key=key,
        tempo_bpm=tempo,
        structure=structure,
        lyrics=placeholder_lyrics,
        arrangement={
            "instruments": instruments,
            "dynamics": "verse-thin → chorus-full → bridge-flip",
        },
        production={"palette": "warm, intimate", "reference_hint": "see knowledge/genres/"},
        council_log=council_log,
    )
