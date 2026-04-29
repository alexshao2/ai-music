"""Cross-session lessons store.

Persistent memory of "what went wrong on this kind of brief" so the
council can avoid repeating the same Critic complaints across runs.

How it fits in:

1. After each compose run the orchestrator calls :func:`record_lessons`
   with the brief, Critic's output, deterministic compliance issues
   (see :mod:`app.services.compliance`) and Lyricist validator issues
   (see :mod:`app.services.lyric_quality`). Each issue becomes one row.

2. Before a persona's first attempt the orchestrator calls
   :func:`recent_lessons_for` and prepends the result to that
   persona's user prompt. The persona thus enters the turn already
   knowing "for V-pop ballad / hoài niệm briefs you previously got
   chấm vì cliche_detected and suno_style_too_long".

This is the cheapest possible "self-learning" mechanism: no
fine-tune, no embeddings, no RAG — just a SQLite table keyed by a
normalised brief signature. When the DB is unavailable (read-only
filesystem in CI, deliberate ``COUNCIL_LESSONS_DISABLED=1``) the
module degrades to a silent no-op so it never blocks compose.
"""
from __future__ import annotations

import logging
import os
import sqlite3
import threading
import time
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)


# --- Configuration --------------------------------------------------------


def _default_db_path() -> Path:
    """Resolve the default SQLite path (under ``backend/app/data/``)."""
    return Path(__file__).resolve().parent.parent / "data" / "lessons.sqlite"


def _resolve_db_path() -> Path:
    """Path used at runtime — overridable via ``COUNCIL_LESSONS_DB``.

    Re-evaluated on every call so tests can ``monkeypatch.setenv`` and
    point at a tmp path without re-importing the module.
    """
    override = os.environ.get("COUNCIL_LESSONS_DB")
    if override:
        return Path(override)
    return _default_db_path()


def _is_disabled() -> bool:
    """When set, all read/write APIs become no-ops.

    Used in CI / tests / read-only environments to keep compose
    deterministic regardless of DB state.
    """
    flag = os.environ.get("COUNCIL_LESSONS_DISABLED", "").strip().lower()
    return flag in {"1", "true", "yes", "on"}


# --- Schema + connection management ---------------------------------------


_SCHEMA = """
CREATE TABLE IF NOT EXISTS lessons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    brief_signature TEXT NOT NULL,
    persona_role   TEXT NOT NULL,
    issue_kind     TEXT NOT NULL,
    issue_code     TEXT NOT NULL,
    issue_message  TEXT NOT NULL,
    created_at     REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_lessons_brief_role
    ON lessons (brief_signature, persona_role, created_at DESC);
"""


# Cap rows per (brief_signature, persona_role) to keep prompt-time
# queries cheap and the DB from growing unbounded.
_PER_BUCKET_CAP = 200

# How many recent entries we feed back into a persona's prompt.
_PROMPT_TOP_N = 3

# A simple module-level lock keeps concurrent compose calls from
# stepping on each other when SQLite is not in WAL mode (sqlite3
# defaults to rollback journal). The lock is per-process — different
# uvicorn workers each have their own, but each worker serialises
# its own writes.
_db_lock = threading.Lock()


def _connect(path: Path) -> sqlite3.Connection:
    """Open (and lazily create) the SQLite DB at ``path``.

    Caller is responsible for closing. Errors propagate so callers
    can convert to no-op behaviour without masking real issues.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=2.0, isolation_level=None)
    conn.executescript(_SCHEMA)
    return conn


# --- Brief signature ------------------------------------------------------


def _normalise_field(value: str | None) -> str:
    """Lowercase + strip + collapse whitespace, never None."""
    if not value:
        return ""
    return " ".join(str(value).strip().lower().split())


def brief_signature(
    *,
    language: str | None,
    genre: str | None,
    mood: str | None,
) -> str:
    """Compute the lookup key for a brief.

    Three axes were chosen because the Critic complaints we've seen
    cluster on them: language drives lyric/imagery rules, genre picks
    cookbook expectations, mood drives harmony/tempo defaults.
    Different references, durations or notes do NOT change the
    signature — they don't materially shift which Critic complaints
    recur.
    """
    return "|".join(
        [
            _normalise_field(language),
            _normalise_field(genre),
            _normalise_field(mood),
        ]
    )


# --- Public dataclass (read API) ------------------------------------------


@dataclass(frozen=True)
class Lesson:
    """A single recorded Critic / compliance complaint."""

    persona_role: str
    issue_kind: str
    issue_code: str
    issue_message: str
    created_at: float


# --- Recording API --------------------------------------------------------


def record_lessons(
    signature: str,
    items: Iterable[Mapping[str, Any]],
) -> int:
    """Persist a batch of lessons. Returns rows actually inserted.

    Each ``item`` is a mapping with ``persona_role``, ``issue_kind``
    (``compliance`` / ``quality`` / ``lyric``), ``issue_code`` and
    ``issue_message``. Any missing/empty field is skipped silently —
    we'd rather lose one row than crash compose.

    Operates inside a single transaction with a row-cap purge per
    bucket so the table stays bounded.
    """
    if _is_disabled() or not signature:
        return 0
    rows: list[tuple[str, str, str, str, str, float]] = []
    now = time.time()
    for raw in items:
        if not isinstance(raw, Mapping):
            continue
        role = _normalise_field(raw.get("persona_role"))
        kind = _normalise_field(raw.get("issue_kind"))
        code = _normalise_field(raw.get("issue_code"))
        message = str(raw.get("issue_message") or "").strip()
        if not (role and kind and code and message):
            continue
        rows.append((signature, role, kind, code, message, now))
    if not rows:
        return 0

    inserted = 0
    try:
        with _db_lock:
            conn = _connect(_resolve_db_path())
            try:
                conn.execute("BEGIN")
                conn.executemany(
                    "INSERT INTO lessons "
                    "(brief_signature, persona_role, issue_kind, issue_code, "
                    "issue_message, created_at) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    rows,
                )
                inserted = len(rows)
                _purge_excess_rows(conn, signature)
                conn.execute("COMMIT")
            finally:
                conn.close()
    except sqlite3.Error as exc:
        log.warning("lessons.record_lessons failed: %s", exc)
        return 0
    return inserted


def _purge_excess_rows(conn: sqlite3.Connection, signature: str) -> None:
    """Trim each (signature, role) bucket to :data:`_PER_BUCKET_CAP`.

    We keep the newest rows. Queries always order by recency anyway,
    so older complaints had marginal value past the cap.
    """
    roles = [
        r[0]
        for r in conn.execute(
            "SELECT DISTINCT persona_role FROM lessons WHERE brief_signature = ?",
            (signature,),
        )
    ]
    for role in roles:
        conn.execute(
            "DELETE FROM lessons WHERE id IN ("
            "  SELECT id FROM lessons "
            "  WHERE brief_signature = ? AND persona_role = ? "
            "  ORDER BY created_at DESC, id DESC "
            "  LIMIT -1 OFFSET ?"
            ")",
            (signature, role, _PER_BUCKET_CAP),
        )


# --- Read API -------------------------------------------------------------


def recent_lessons_for(
    signature: str,
    persona_role: str,
    *,
    limit: int = _PROMPT_TOP_N,
) -> list[Lesson]:
    """Return the most recent ``limit`` lessons for this signature+role.

    Empty list when the DB is missing, the bucket is empty, or the
    module is disabled. Never raises — callers can safely splice the
    result into a prompt without try/except.
    """
    if _is_disabled() or not signature or not persona_role or limit <= 0:
        return []
    role = _normalise_field(persona_role)
    if not role:
        return []
    try:
        path = _resolve_db_path()
        if not path.exists():
            return []
        with _db_lock:
            conn = _connect(path)
            try:
                cursor = conn.execute(
                    "SELECT persona_role, issue_kind, issue_code, "
                    "issue_message, created_at FROM lessons "
                    "WHERE brief_signature = ? AND persona_role = ? "
                    "ORDER BY created_at DESC, id DESC LIMIT ?",
                    (signature, role, int(limit)),
                )
                return [
                    Lesson(
                        persona_role=row[0],
                        issue_kind=row[1],
                        issue_code=row[2],
                        issue_message=row[3],
                        created_at=float(row[4]),
                    )
                    for row in cursor.fetchall()
                ]
            finally:
                conn.close()
    except sqlite3.Error as exc:
        log.warning("lessons.recent_lessons_for failed: %s", exc)
        return []


# --- Prompt formatting ----------------------------------------------------


def format_lessons_for_prompt(lessons: list[Lesson]) -> str:
    """Render lessons as a "prior brief had these recurring issues" block.

    Returns ``""`` for an empty list so callers can simply concatenate
    without conditionals.
    """
    if not lessons:
        return ""
    bullets = []
    for lesson in lessons:
        bullets.append(
            f"- ({lesson.issue_kind}/{lesson.issue_code}) {lesson.issue_message}"
        )
    return (
        "## BRIEF NÀY TRƯỚC ĐÂY HAY MẮC — TRÁNH LẶP LẠI\n"
        "Trên các session trước, chuyên gia ở vai trò của bạn đã bị "
        "Critic chấm các lỗi sau cho brief tương tự:\n"
        + "\n".join(bullets)
        + "\nLần này hãy chủ động tránh và sửa NGAY trong contribution đầu "
        "tiên — đừng để Critic phải nhắc lại.\n"
    )


# --- Higher-level convenience --------------------------------------------


def collect_lessons_from_run(
    *,
    compliance_issues: Iterable[Any] | None = None,
    quality_concerns_by_role: Mapping[str, Iterable[tuple[str, float]]] | None = None,
    lyric_issues: Iterable[Any] | None = None,
) -> list[dict[str, str]]:
    """Convert a single compose run's findings into ``record_lessons`` rows.

    Each input source uses a slightly different shape, so we
    normalise here:

    * ``compliance_issues`` — :class:`app.services.compliance.ComplianceIssue`
      objects (have ``persona_role``, ``code``, ``message``).
    * ``quality_concerns_by_role`` — ``{role: [(dimension, score), ...]}``
      from :func:`council._quality_concerns_by_role`.
    * ``lyric_issues`` — :class:`app.services.lyric_quality.LyricIssue`
      (have ``code``, ``message``; persona is always ``lyricist``).

    Returns a list of dicts ready to feed into :func:`record_lessons`.
    """
    out: list[dict[str, str]] = []
    for issue in compliance_issues or []:
        role = getattr(issue, "persona_role", None) or ""
        code = getattr(issue, "code", None) or ""
        message = getattr(issue, "message", None) or ""
        if role and code and message:
            out.append(
                {
                    "persona_role": role,
                    "issue_kind": "compliance",
                    "issue_code": code,
                    "issue_message": message,
                }
            )
    if quality_concerns_by_role:
        for role, items in quality_concerns_by_role.items():
            for dim, score in items or []:
                out.append(
                    {
                        "persona_role": role,
                        "issue_kind": "quality",
                        "issue_code": str(dim),
                        "issue_message": (
                            f"Critic chấm {float(score):.1f}/10 cho "
                            f"chiều {dim}."
                        ),
                    }
                )
    for issue in lyric_issues or []:
        code = getattr(issue, "code", None) or ""
        message = getattr(issue, "message", None) or ""
        if code and message:
            out.append(
                {
                    "persona_role": "lyricist",
                    "issue_kind": "lyric",
                    "issue_code": code,
                    "issue_message": message,
                }
            )
    return out


__all__ = [
    "Lesson",
    "brief_signature",
    "collect_lessons_from_run",
    "format_lessons_for_prompt",
    "record_lessons",
    "recent_lessons_for",
]
