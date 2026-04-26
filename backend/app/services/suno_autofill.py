"""Suno automation: drive a CDP-attached Chrome (already logged in) to create a song.

Why CDP and not the public Suno API?
  Suno does not expose a public guest API. We assume the user has already logged
  into Suno in a Chrome instance running with `--remote-debugging-port=29229`
  (the default in this dev environment). We attach Playwright over CDP so we
  inherit the existing authenticated session and cookies.

What this module does:
  1. Connect to the CDP endpoint.
  2. Reuse the existing Suno tab if one is open, otherwise open a new tab.
  3. Navigate to ``suno.com/create`` and switch the panel to **Advanced** mode.
  4. Fill the Lyrics, Styles, and Title fields.
  5. Click **Create** and (optionally) poll the workspace until the new song
     appears, then return the share URL.

Notes on selectors (verified against suno.com on 2026-04-26):
  * Lyrics:  ``textarea[data-testid="lyrics-textarea"]`` (only one such element)
  * Styles:  ``textarea[maxlength="1000"]`` (only the styles field has this cap)
  * Title:   ``input[placeholder="Song Title (Optional)"]`` — there are two in
             the DOM (Simple + Advanced), only one is visible at a time. We pick
             the visible one programmatically.
  * Create:  the button whose accessible name is exactly "Create".

This is a best-effort scraper. Selectors can break when Suno ships UI changes,
so callers must tolerate ``SunoAutofillError`` and surface the message back to
the user.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass

from playwright.sync_api import (
    Browser,
    Locator,
    Page,
    sync_playwright,
)
from playwright.sync_api import (
    TimeoutError as PlaywrightTimeoutError,
)

from app.config import settings
from app.schemas import SongDraft
from app.services.suno import build_prompt

log = logging.getLogger(__name__)

DEFAULT_CDP_URL = "http://localhost:29229"
SUNO_CREATE_URL = "https://suno.com/create"


class SunoAutofillError(RuntimeError):
    """Raised when we can't drive the Suno UI (selectors moved, login expired,
    CDP unreachable, etc.). Always carries a human-readable message."""


@dataclass
class SunoAutofillResult:
    submitted: bool
    title: str
    style: str
    lyrics_chars: int
    suno_url: str | None  # None if we didn't wait for completion
    note: str | None = None


def autofill_and_generate(
    draft: SongDraft,
    *,
    wait_for_song: bool = True,
    timeout_sec: int = 180,
    cdp_url: str | None = None,
) -> SunoAutofillResult:
    """Fill the Suno Create form from a draft and click Create.

    Parameters
    ----------
    draft : SongDraft
        The composed draft. Title, style, and lyrics are derived via
        :func:`app.services.suno.build_prompt` so they match what the manual
        "Mở Suno" launcher copies to the clipboard.
    wait_for_song : bool
        If ``True``, poll the My Workspace panel until a new song row appears
        and return its share URL. If ``False``, return immediately after
        clicking Create.
    timeout_sec : int
        Total budget for the whole flow including any wait_for_song poll.
    cdp_url : str | None
        Override for ``http://localhost:29229``. Useful for tests.
    """
    prompt = build_prompt(draft)
    cdp = cdp_url or getattr(settings, "suno_cdp_url", None) or DEFAULT_CDP_URL

    log.info("Suno autofill starting (cdp=%s, wait=%s)", cdp, wait_for_song)
    with sync_playwright() as p:
        try:
            browser = p.chromium.connect_over_cdp(cdp)
        except Exception as exc:  # noqa: BLE001
            raise SunoAutofillError(
                f"Cannot connect to Chrome CDP at {cdp}. Make sure Chrome is running "
                f"with --remote-debugging-port=29229 and the user is logged into Suno."
            ) from exc

        page = _get_or_open_suno_page(browser)
        try:
            _ensure_advanced_mode(page)
            _fill_form(page, style=prompt.style, lyrics=prompt.lyrics, title=prompt.title)
            _click_create(page)

            suno_url: str | None = None
            note: str | None = None
            if wait_for_song:
                try:
                    suno_url = _wait_for_new_song(page, timeout_sec=timeout_sec)
                except PlaywrightTimeoutError:
                    note = (
                        f"Submitted but song did not finish generating within "
                        f"{timeout_sec}s. Check Suno My Workspace tab manually."
                    )
                    log.warning("Suno generation timed out after %ss", timeout_sec)

            return SunoAutofillResult(
                submitted=True,
                title=prompt.title,
                style=prompt.style,
                lyrics_chars=len(prompt.lyrics),
                suno_url=suno_url,
                note=note,
            )
        finally:
            # We do NOT close the browser — it is the user's persistent Chrome.
            pass


# ---------- Helpers ----------


def _get_or_open_suno_page(browser: Browser) -> Page:
    for ctx in browser.contexts:
        for pg in ctx.pages:
            if "suno.com" in pg.url:
                pg.bring_to_front()
                if "/create" not in pg.url:
                    pg.goto(SUNO_CREATE_URL, wait_until="domcontentloaded")
                return pg
    # No Suno tab open — make one in the first context.
    ctx = browser.contexts[0] if browser.contexts else browser.new_context()
    page = ctx.new_page()
    page.goto(SUNO_CREATE_URL, wait_until="domcontentloaded")
    page.bring_to_front()
    return page


def _ensure_advanced_mode(page: Page) -> None:
    """Click the Advanced toggle if Simple is currently selected.

    Idempotent — clicking Advanced when already in Advanced is a no-op.
    """
    try:
        page.get_by_role("button", name="Advanced", exact=True).first.click(timeout=5000)
    except PlaywrightTimeoutError as exc:
        raise SunoAutofillError(
            "Cannot find the 'Advanced' toggle on Suno's create page. "
            "Suno's UI may have changed — autofill needs an update."
        ) from exc
    page.wait_for_timeout(400)


def _fill_form(page: Page, *, style: str, lyrics: str, title: str) -> None:
    """Fill style, lyrics, and title. Each fill is bounded so we fail fast."""
    try:
        page.locator('textarea[data-testid="lyrics-textarea"]').fill(lyrics, timeout=10000)
    except PlaywrightTimeoutError as exc:
        raise SunoAutofillError("Cannot find Suno's Lyrics textarea.") from exc

    try:
        page.locator('textarea[maxlength="1000"]').first.fill(style, timeout=10000)
    except PlaywrightTimeoutError as exc:
        raise SunoAutofillError("Cannot find Suno's Styles textarea.") from exc

    title_inputs = page.locator('input[placeholder="Song Title (Optional)"]')
    visible_title = _first_visible(title_inputs)
    if visible_title is None:
        raise SunoAutofillError("Cannot find a visible Song Title input.")
    visible_title.fill(title)
    page.wait_for_timeout(300)


def _first_visible(locator: Locator) -> Locator | None:
    count = locator.count()
    for i in range(count):
        cand = locator.nth(i)
        try:
            if cand.is_visible():
                return cand
        except Exception:  # noqa: BLE001
            continue
    return None


def _click_create(page: Page) -> None:
    """Click the main "Create" form button at the bottom of the form.

    Suno's page exposes multiple Create-ish controls:
      * a sidebar icon button whose tooltip is "Create New Workspace" (width ~16px),
      * the orange form submit, whose accessible name is **"Create song"** via
        ``aria-label`` even though the visible text is just "Create" (~350px wide).

    Strategy: prefer the explicit ``aria-label="Create song"`` selector. Fall back
    to scanning ``button:has-text("Create")`` and picking the widest visible one
    so we don't regress if Suno renames the aria-label.
    """
    page.wait_for_timeout(400)
    primary = page.locator('button[aria-label="Create song"]')
    try:
        primary.first.wait_for(state="visible", timeout=5000)
        target: Locator = primary.first
    except PlaywrightTimeoutError:
        target = _widest_visible(page.locator('button:has-text("Create")'))
        if target is None:
            raise SunoAutofillError(  # noqa: B904
                "Cannot find the form 'Create' button. Suno's UI may have changed."
            )

    if target.is_disabled():
        raise SunoAutofillError(
            "The Create button is disabled. Suno likely rejected one of the inputs "
            "(lyrics empty, style empty, or no credits)."
        )
    target.click()


def _widest_visible(locator: Locator, *, min_width: float = 100.0) -> Locator | None:
    """Return the visible candidate with the largest bounding-box width, or None.

    Used to disambiguate between a narrow icon button and a wide form button
    when both share the same role/text.
    """
    best: Locator | None = None
    best_width = min_width
    for i in range(locator.count()):
        cand = locator.nth(i)
        try:
            if not cand.is_visible():
                continue
            box = cand.bounding_box()
        except Exception:  # noqa: BLE001
            continue
        if not box:
            continue
        width = float(box["width"])
        if width > best_width:
            best = cand
            best_width = width
    return best


def _wait_for_new_song(page: Page, *, timeout_sec: int) -> str | None:
    """Poll the workspace panel until a new song with a share URL appears.

    Suno renders the workspace song list on the right side of /create. Each row
    eventually exposes an anchor like ``<a href="/song/<uuid>">``. We snapshot
    the set of song hrefs at start, then poll for the first new one.
    """
    initial = _current_song_links(page)
    deadline = time.monotonic() + timeout_sec
    poll_interval = 4.0
    while time.monotonic() < deadline:
        page.wait_for_timeout(int(poll_interval * 1000))
        latest = _current_song_links(page)
        new_links = [link for link in latest if link not in initial]
        if new_links:
            return new_links[0]
    raise PlaywrightTimeoutError(f"No new song row appeared in {timeout_sec}s.")


def _current_song_links(page: Page) -> set[str]:
    try:
        hrefs = page.eval_on_selector_all(
            'a[href*="/song/"]',
            "els => els.map(e => e.getAttribute('href'))",
        )
    except Exception:  # noqa: BLE001
        return set()
    return {h for h in hrefs if h}
