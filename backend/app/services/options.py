"""Brief option lists for the composition UI.

The UI needs predefined choices instead of free-text inputs so users don't
have to hand-craft genre/mood strings (and so the council has consistent
labels to RAG against).

- **Genres** are derived from ``knowledge/genres/*.md`` frontmatter — adding
  a new genre cookbook automatically surfaces it in the UI without touching
  the frontend. We classify each genre into a UI group (V-pop / K-pop /
  English / Latin / Hip-hop / Other) by inspecting its tag list.
- **Moods** are curated here. Lyric/melody mood vocabulary needs to stay
  short and tonally distinctive, so we don't pull from RAG corpus the way
  we do for genres.
- **Languages** mirror the existing :class:`~app.schemas.Brief.language`
  values so the FE doesn't have to hardcode them in two places.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.services import knowledge as knowledge_svc

# UI groups for genres. Order matters — used as render order in the FE.
_GENRE_GROUP_ORDER: tuple[str, ...] = (
    "vpop",
    "kpop",
    "jpop",
    "english",
    "latin",
    "hiphop",
    "electronic",
    "other",
)

_GROUP_LABELS: dict[str, str] = {
    "vpop": "V-pop / Việt",
    "kpop": "K-pop",
    "jpop": "J-pop / Anime",
    "english": "English / Pop quốc tế",
    "latin": "Latin",
    "hiphop": "Hip-hop / Rap",
    "electronic": "Electronic / Dance",
    "other": "Khác",
}

# Tag keywords that map a genre file into a UI group. Checked in declaration
# order; first match wins so more specific groups (vpop > english) come first.
_GROUP_TAG_RULES: tuple[tuple[str, frozenset[str]], ...] = (
    ("vpop", frozenset({"vpop", "vrap", "vinahouse", "bolero", "cai-luong", "vietnamese"})),
    ("kpop", frozenset({"kpop", "korean"})),
    ("jpop", frozenset({"jpop", "japanese", "anime", "citypop"})),
    (
        "latin",
        frozenset(
            {"latin", "spanish", "reggaeton", "bachata", "bolero-latin"}
        ),
    ),
    (
        "hiphop",
        frozenset(
            {
                "hip-hop",
                "hiphop",
                "rap",
                "trap",
                "boom-bap",
                "drill",
            }
        ),
    ),
    (
        "electronic",
        frozenset(
            {
                "edm",
                "electronic",
                "synthwave",
                "house",
                "techno",
                "lofi",
                "festival",
            }
        ),
    ),
    (
        "english",
        frozenset(
            {
                "english",
                "pop",
                "ballad",
                "rnb",
                "soul",
                "country",
                "rock",
                "metal",
                "indie",
                "folk",
                "jazz",
                "classical",
                "reggae",
            }
        ),
    ),
)


@dataclass(frozen=True)
class GenreOption:
    """One row in the FE genre picker."""

    slug: str
    """Stable id used for ``brief.genre``. Equals the markdown file stem."""

    label: str
    """Human-readable display string. Comes from frontmatter ``title``."""

    group: str
    """UI section the option lives under (see :data:`_GENRE_GROUP_ORDER`)."""

    tags: tuple[str, ...]
    """Frontmatter tags — surfaced for advanced users / debugging."""

    knowledge_path: str
    """Relative markdown path; the council uses this for RAG retrieval."""


@dataclass(frozen=True)
class MoodOption:
    """One row in the FE mood picker."""

    slug: str
    """Stable id used for ``brief.mood``. Latin slug for stable storage."""

    label: str
    """Display string in the picker (Vietnamese)."""

    group: str
    """UI section, e.g. 'Buồn', 'Năng lượng'."""

    keywords: tuple[str, ...]
    """Extra hints prepended to ``brief.mood`` to bias persona retrieval."""


# Curated mood list. Slugs are stable so existing drafts keep their meaning.
# Vietnamese labels — matches the dominant audience of the app. Keywords are
# what the personas read; multiple synonyms help with both prompt embedding
# and human readability when the FE shows "+ keywords" tooltip.
MOOD_OPTIONS: tuple[MoodOption, ...] = (
    MoodOption("hoai-niem", "Hoài niệm, dịu dàng", "Hoài niệm", ("nostalgic", "wistful", "tender")),
    MoodOption("buon-sau", "Buồn sâu, day dứt", "Buồn", ("melancholic", "aching", "longing")),
    MoodOption("co-don", "Cô đơn, lạnh giá", "Buồn", ("lonely", "isolated", "cold")),
    MoodOption("chia-ly", "Chia ly, tiếc nuối", "Buồn", ("breakup", "regret", "farewell")),
    MoodOption("vui-tuoi", "Vui tươi, trong sáng", "Năng lượng", ("bright", "joyful", "sunny")),
    MoodOption("song-dong", "Sống động, bùng nổ", "Năng lượng", ("energetic", "explosive", "anthemic")),
    MoodOption("tu-tin", "Tự tin, ngạo nghễ", "Năng lượng", ("confident", "swagger", "bold")),
    MoodOption("ngot-ngao", "Ngọt ngào, lãng mạn", "Yêu", ("romantic", "sweet", "intimate")),
    MoodOption("tha-thiet", "Tha thiết, khao khát", "Yêu", ("yearning", "passionate", "earnest")),
    MoodOption("ru-tinh", "Ru tình, êm đềm", "Yêu", ("soothing", "lullaby", "soft")),
    MoodOption("triet-ly", "Triết lý, suy tưởng", "Triết lý", ("contemplative", "philosophical", "introspective")),
    MoodOption("hy-vong", "Hy vọng, vươn lên", "Hy vọng", ("hopeful", "uplifting", "rising")),
    MoodOption("biet-on", "Biết ơn, ấm áp", "Hy vọng", ("grateful", "warm", "homely")),
    MoodOption("phan-no", "Phẫn nộ, dằn vặt", "Mạnh", ("angry", "tormented", "bitter")),
    MoodOption("u-toi", "U tối, ám ảnh", "Mạnh", ("dark", "haunting", "ominous")),
    MoodOption("mong-mo", "Mộng mơ, huyền ảo", "Mộng", ("dreamy", "ethereal", "surreal")),
    MoodOption("hoai-co", "Hoài cổ, retro", "Mộng", ("retro", "vintage", "nostalgic")),
    MoodOption("tre-trung", "Trẻ trung, viral", "Năng lượng", ("youthful", "viral", "playful")),
    MoodOption("kien-cuong", "Kiên cường, vượt khó", "Hy vọng", ("resilient", "overcome", "determined")),
    MoodOption("bi-trang", "Bi tráng, hùng hồn", "Mạnh", ("epic", "heroic", "tragic")),
)


def _group_for_tags(tags: tuple[str, ...]) -> str:
    """Classify a genre by its tag list. First matching rule wins."""
    tag_set = {t.lower() for t in tags}
    for group, keywords in _GROUP_TAG_RULES:
        if tag_set & keywords:
            return group
    return "other"


def list_genres() -> list[GenreOption]:
    """All genre cookbooks under ``knowledge/genres/`` as picker options.

    Sort order is (group_order, label) so the FE can iterate linearly and
    render `<optgroup>` boundaries on group changes.
    """
    docs = knowledge_svc.all_docs()
    options: list[GenreOption] = []
    for doc in docs:
        if not doc.path.startswith("genres/"):
            continue
        slug = doc.path.removeprefix("genres/").removesuffix(".md")
        group = _group_for_tags(doc.tags)
        options.append(
            GenreOption(
                slug=slug,
                label=doc.title,
                group=group,
                tags=doc.tags,
                knowledge_path=doc.path,
            )
        )
    group_index = {g: i for i, g in enumerate(_GENRE_GROUP_ORDER)}
    options.sort(key=lambda o: (group_index.get(o.group, 99), o.label))
    return options


def list_moods() -> list[MoodOption]:
    return list(MOOD_OPTIONS)


def group_label(group: str) -> str:
    """Human-readable label for a genre group slug."""
    return _GROUP_LABELS.get(group, group)


__all__ = [
    "GenreOption",
    "MoodOption",
    "MOOD_OPTIONS",
    "list_genres",
    "list_moods",
    "group_label",
]
