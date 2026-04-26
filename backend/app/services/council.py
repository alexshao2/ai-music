"""Council personas and orchestration logic.

M0: deterministic stubs that produce a coherent draft from a brief without calling
an LLM. M2 will swap these stubs for real LLM calls with retrieved knowledge.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass

from app.schemas import Brief, CouncilTurn, Section, SongDraft


@dataclass(frozen=True)
class Persona:
    name: str
    role: str
    expertise_tags: tuple[str, ...]
    system_prompt: str


COUNCIL_PERSONAS: tuple[Persona, ...] = (
    Persona(
        name="Music Theorist",
        role="theorist",
        expertise_tags=("theory", "harmony", "mode", "voice-leading"),
        system_prompt=(
            "Bạn là nhà lý thuyết âm nhạc trong hội đồng. "
            "Đề xuất key/mode, vòng hợp âm, và cấu trúc hoà âm phù hợp với brief. "
            "Ngắn gọn, đi vào quyết định cụ thể."
        ),
    ),
    Persona(
        name="Composer",
        role="composer",
        expertise_tags=("melody", "motif", "songwriting"),
        system_prompt=(
            "Bạn là nhà soạn nhạc. Đề xuất motif giai điệu, cấu trúc bài hát "
            "(intro/verse/chorus/bridge/outro), và hook melodic."
        ),
    ),
    Persona(
        name="Lyricist",
        role="lyricist",
        expertise_tags=("lyrics", "prosody", "rhyme"),
        system_prompt=(
            "Bạn là nhà viết lời. Đề xuất theme, hook, và nháp lời theo cấu trúc. "
            "Tôn trọng ngôn ngữ và mood trong brief."
        ),
    ),
    Persona(
        name="Arranger",
        role="arranger",
        expertise_tags=("arrangement", "instrumentation", "dynamics"),
        system_prompt=(
            "Bạn là nhà phối khí. Đề xuất nhạc cụ theo từng section và đường cong "
            "dynamics (build-up, drop)."
        ),
    ),
    Persona(
        name="Producer",
        role="producer",
        expertise_tags=("production", "sound", "mix", "genre"),
        system_prompt=(
            "Bạn là nhà sản xuất. Đề xuất sound palette, 3–5 bài tham chiếu, và "
            "đặc tính âm thanh nên có."
        ),
    ),
    Persona(
        name="A&R Critic",
        role="critic",
        expertise_tags=("market", "originality", "cliche"),
        system_prompt=(
            "Bạn là nhà phê bình A&R. Phản biện thẳng thắn các đề xuất của hội đồng: "
            "chỉ ra cliché, điểm yếu, và đề xuất cải tiến."
        ),
    ),
)


# ---------- Heuristic helpers (M0 stubs, no LLM) ----------

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
        # i–VI–III–VII for minor
        # Simple stand-in chord names; not transposed beyond root
        return [f"{root}m", "F", "C", "G"] if root == "A" else [f"{root}m", "VI", "III", "VII"]
    root = key.split()[0]
    return [root, "G", "Am", "F"] if root == "C" else [root, "V", "vi", "IV"]


# ---------- Public API ----------


def clarifying_questions(brief: Brief) -> list[str]:
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


def compose(brief: Brief) -> SongDraft:
    """Build a Song Draft deterministically from a brief (M0 stub)."""
    key, tempo = _pick_key_tempo(brief)
    chords = _default_progression(key)
    instruments = _pick_instruments(brief)

    structure = [
        Section(section="intro", bars=4, chords=chords[:2], notes="Mở mood, nhạc cụ thưa."),
        Section(section="verse", bars=16, chords=chords, notes="Thiết lập câu chuyện."),
        Section(section="pre_chorus", bars=8, chords=chords[1:] + chords[:1], notes="Đẩy năng lượng."),
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
        arrangement={"instruments": instruments, "dynamics": "verse-thin → chorus-full → bridge-flip"},
        production={"palette": "warm, intimate", "reference_hint": "see knowledge/genres/"},
        council_log=council_log,
    )
