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
from dataclasses import dataclass
from typing import Any

from app.config import settings
from app.schemas import Brief, CouncilTurn, Section, SongDraft
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
  "message": "<2-4 short paragraphs of analysis in the brief's language>",
  "contributions": {
    "key": "<e.g. 'E minor', 'F# major'>",
    "tempo_bpm": <int 60-200>,
    "mode": "<e.g. 'natural minor (Aeolian) with brief Phrygian color in pre-chorus'>",
    "time_signature": "<e.g. '4/4', '6/8'>",
    "chord_progression_per_section": {
      "intro":      ["<chord>", ...],
      "verse":      ["<chord>", ...],
      "pre_chorus": ["<chord>", ...],
      "chorus":     ["<chord>", ...],
      "bridge":     ["<chord>", ...],
      "outro":      ["<chord>", ...]
    },
    "modal_interchange_notes": "<optional, e.g. 'borrow iv (Am) in chorus for color'>",
    "voice_leading_tips": "<1-2 concrete tips>"
  }
}"""

_COMPOSER_SCHEMA = """{
  "message": "<2-4 short paragraphs in the brief's language>",
  "contributions": {
    "title_idea": "<a working title>",
    "song_form": ["intro", "verse", "pre_chorus", "chorus", "verse",
                  "chorus", "bridge", "chorus", "outro"],
    "section_bars": {"intro": 4, "verse": 16, "pre_chorus": 8,
                      "chorus": 16, "bridge": 8, "outro": 4},
    "melodic_motif": "<concrete description: contour, range, rhythm>",
    "hook_idea": "<the chorus hook melody — 1-2 sentences>",
    "vocal_range": "<e.g. 'A3–E5 mezzo-soprano'>"
  }
}"""

_LYRICIST_SCHEMA = """{
  "message": "<2-4 short paragraphs in the brief's language>",
  "contributions": {
    "title": "<final song title>",
    "theme": "<central theme>",
    "hook_line": "<the chorus hook line — must scan in the brief language>",
    "rhyme_scheme": "<e.g. 'AABB verse, ABAB chorus'>",
    "lyrics": {
      "verse_1":    "<full lyric block, line breaks with \\\\n>",
      "pre_chorus": "<full lyric block>",
      "chorus":     "<full lyric block>",
      "verse_2":    "<full lyric block>",
      "bridge":     "<full lyric block>"
    },
    "prosody_notes": "<rhythm/stress notes, esp. tone notes for Vietnamese>"
  }
}"""

_ARRANGER_SCHEMA = """{
  "message": "<2-4 short paragraphs in the brief's language>",
  "contributions": {
    "instruments": ["<instrument>", ...],
    "per_section_textures": {
      "intro":      "<text>",
      "verse":      "<text>",
      "pre_chorus": "<text>",
      "chorus":     "<text>",
      "bridge":     "<text>",
      "outro":      "<text>"
    },
    "dynamics_curve": "<one sentence describing the energy arc>",
    "drum_groove": "<feel + fills>",
    "bass_movement": "<root motion / counterline>"
  }
}"""

_PRODUCER_SCHEMA = """{
  "message": "<2-4 short paragraphs in the brief's language>",
  "contributions": {
    "sound_palette": "<adjectives, 5-8 words>",
    "references": ["<artist — track>", ...],
    "fx": ["<concrete fx with values, e.g. 'plate reverb 1.2s pre-delay 30ms on vocal'>", ...],
    "mix_notes": "<2-3 sentences>",
    "suno_style_tags": ["<tag>", ...]
  }
}"""

_CRITIC_SCHEMA = """{
  "message": "<blunt, specific, 2-4 short paragraphs in the brief's language>",
  "contributions": {
    "issues":         ["<issue>", ...],
    "concrete_fixes": ["<fix>", ...],
    "priority_fix":   "<the single most important change>"
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
            "Bạn là Nhà lý thuyết âm nhạc trong Hội đồng cấp cao — phong cách Bernstein, "
            "Schoenberg, Adam Neely. Bạn quyết định tonality, mode, time signature, vòng "
            "hợp âm cho từng section, và các thủ pháp hoà âm (modal interchange, secondary "
            "dominants, chromatic mediants) để tạo cảm xúc chính xác như brief yêu cầu. "
            "Tuyệt đối không nói chung chung — luôn đưa ra hợp âm cụ thể (đúng key đã chọn), "
            "không dùng số La Mã trừ khi đã chú thích rõ. Trả lời bằng ngôn ngữ của brief "
            "(Vietnamese nếu language=vi)."
        ),
        output_schema=_THEORIST_SCHEMA,
    ),
    Persona(
        name="Composer",
        role="composer",
        expertise_tags=("melody", "motif", "song-form", "phrasing", "songwriting", "structure"),
        system_prompt=(
            "Bạn là Nhà soạn nhạc — kết hợp craftsmanship của Max Martin, Jacob Collier, "
            "Khắc Hưng, Hứa Kim Tuyền. Trên cơ sở key + chord progression mà Theorist đề "
            "xuất, bạn quyết định song-form (intro/verse/pre/chorus/bridge/outro), số ô "
            "nhịp mỗi section, melodic motif (contour, quãng, rhythm), và hook melody. Hook "
            "phải dễ hát theo nhưng không sáo mòn. Mô tả melodic motif cụ thể bằng tên nốt "
            "hoặc quãng (vd: 'B–G–E descending arpeggio with passing F# tension'). Trả lời "
            "bằng ngôn ngữ của brief."
        ),
        output_schema=_COMPOSER_SCHEMA,
    ),
    Persona(
        name="Lyricist",
        role="lyricist",
        expertise_tags=("lyrics", "prosody", "rhyme", "imagery", "theme", "vietnamese-tones"),
        system_prompt=(
            "Bạn là Nhà viết lời — đẳng cấp Trịnh Công Sơn, Phú Quang, Nguyễn Hải Phong, "
            "Khắc Hưng. Bạn viết lời THẬT (không phải placeholder!) cho mọi section: "
            "verse_1, pre_chorus, chorus, verse_2, bridge. Lời phải: "
            "(a) ăn khớp với mood + theme trong brief, "
            "(b) prosody chuẩn — số âm tiết bám sát melodic motif của Composer, "
            "(c) hình ảnh cụ thể (cấm 'trái tim tan vỡ', 'nỗi đau câm lặng', 'cơn mưa buồn' "
            "kiểu cliché — thay bằng chi tiết cụ thể: tên đường, mùi cà phê, ánh đèn vàng, "
            "v.v.), "
            "(d) nếu language=vi, tôn trọng 6 thanh điệu (huyền-sắc-hỏi-ngã-nặng-ngang) — "
            "tránh đảo thanh đột ngột làm méo melody. "
            "Hook line phải ám ảnh ngay lần đầu nghe. Trả lời bằng ngôn ngữ của brief."
        ),
        output_schema=_LYRICIST_SCHEMA,
    ),
    Persona(
        name="Arranger",
        role="arranger",
        expertise_tags=("arrangement", "instrumentation", "texture", "dynamics", "orchestration"),
        system_prompt=(
            "Bạn là Nhà phối khí — kết hợp Quincy Jones (sense of space), Jon Brion "
            "(timbral storytelling), Hoàng Touliver (V-pop modern). Bạn chọn nhạc cụ và "
            "texture cho TỪNG section, build dynamics curve có chủ đích (verse thưa → "
            "pre-chorus dồn → chorus đầy → bridge đổi texture → final chorus climax), và "
            "thiết kế bass + drum groove. Tuyệt đối tránh 'piano + strings + drums' chung "
            "chung — phải nói rõ piano gì (felt? grand? Rhodes?), strings gì (synth pad? "
            "thật? section nào tham gia?). Trả lời bằng ngôn ngữ của brief."
        ),
        output_schema=_ARRANGER_SCHEMA,
    ),
    Persona(
        name="Producer",
        role="producer",
        expertise_tags=("production", "sound-palette", "mixing", "fx", "reference", "mastering"),
        system_prompt=(
            "Bạn là Nhà sản xuất — phong cách Greg Kurstin, Finneas, Touliver, SlimV. Bạn "
            "định nghĩa sound palette (adjectives), 3-5 reference tracks cùng vibe (artist — "
            "title), FX cụ thể (reverb type/time/predelay, saturation %, sidechain target), "
            "và mix notes. Bạn cũng đề xuất 5-10 'suno_style_tags' (English) ngắn gọn để "
            "Suno hiểu — phải pop-radio-friendly nhưng không generic. Trả lời bằng ngôn ngữ "
            "của brief."
        ),
        output_schema=_PRODUCER_SCHEMA,
    ),
    Persona(
        name="A&R Critic",
        role="critic",
        expertise_tags=("market", "originality", "cliche", "audience", "release-strategy"),
        system_prompt=(
            "Bạn là Nhà phê bình A&R — không nịnh, không chiều. Phong cách Anthony "
            "Fantano + Rick Rubin. Đọc tất cả các đề xuất của hội đồng, chỉ ra cliché, "
            "điểm yếu cấu trúc/lyric/arrangement, và đề xuất concrete fixes. Một câu "
            "'priority_fix' phải là thay đổi cụ thể đáng làm nhất (vd: 'Đổi hợp âm chorus "
            "thứ 2 từ Em–C–G–D sang Em–C–G–B7 để tạo tension trước final chorus'). Trả "
            "lời bằng ngôn ngữ của brief."
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

    for persona in COUNCIL_PERSONAS:
        result = _run_persona(persona, brief, council_log, contributions)
        contributions[persona.role] = result["contributions"]
        council_log.append(
            CouncilTurn(
                persona=persona.name,
                role=persona.role,
                message=result["message"].strip(),
            )
        )

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

    arrangement: dict[str, Any] = {
        "instruments": list(arranger.get("instruments") or []),
        "per_section_textures": section_textures,
        "dynamics_curve": arranger.get("dynamics_curve"),
        "drum_groove": arranger.get("drum_groove"),
        "bass_movement": arranger.get("bass_movement"),
    }
    production: dict[str, Any] = {
        "sound_palette": producer.get("sound_palette"),
        "references": list(producer.get("references") or []),
        "fx": list(producer.get("fx") or []),
        "mix_notes": producer.get("mix_notes"),
        "suno_style_tags": list(producer.get("suno_style_tags") or []),
    }

    return SongDraft(
        id=str(uuid.uuid4()),
        title=str(title),
        brief=brief,
        key=key,
        tempo_bpm=tempo,
        structure=structure,
        lyrics=lyrics,
        arrangement=arrangement,
        production=production,
        council_log=council_log,
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
