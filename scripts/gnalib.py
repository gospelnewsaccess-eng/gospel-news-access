"""
gnalib.py — the shared toolbox every Gospel News Access script uses.

Plain English: this file does not produce any page by itself. It holds the
jobs that more than one script needs — fetching a web page, reading an RSS
feed, digging a photo out of a story, handling dates in Pacific time. Keeping
them here means a fix happens once instead of four times.

Deliberately uses ONLY Python's built-in library. No pip install, nothing to
break on a runner six months from now.
"""

from __future__ import annotations

import gzip
import hashlib
import html as _html
import io
import json
import os
import re
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from zoneinfo import ZoneInfo

# --------------------------------------------------------------------------
# Paths. Everything is resolved from the repository root so a script behaves
# the same whether it is run from the root or from inside scripts/.
# --------------------------------------------------------------------------
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")

PACIFIC = ZoneInfo("America/Los_Angeles")
UTC = timezone.utc

SITE_URL = "https://gospelnewsaccess-eng.github.io/gospel-news-access"
SITE_NAME = "Gospel News Access"

UA = (
    "Mozilla/5.0 (compatible; GospelNewsAccessBot/1.0; +"
    + SITE_URL
    + ")"
)


# --------------------------------------------------------------------------
# Time helpers
# --------------------------------------------------------------------------
def now_utc() -> datetime:
    return datetime.now(UTC)


def now_pacific() -> datetime:
    return datetime.now(PACIFIC)


def iso(dt: datetime) -> str:
    """Store every timestamp the same way: UTC, ISO 8601, with a Z."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_dt(value) -> datetime | None:
    """Read the many date formats feeds use. Returns None if unreadable."""
    if not value:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    v = str(value).strip()
    # RFC 822 — the usual RSS format: "Tue, 16 Sep 2026 14:03:00 +0000"
    try:
        dt = parsedate_to_datetime(v)
        if dt:
            return dt if dt.tzinfo else dt.replace(tzinfo=UTC)
    except Exception:
        pass
    # ISO 8601 — the usual Atom format
    try:
        dt = datetime.fromisoformat(v.replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=UTC)
    except Exception:
        pass
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(v, fmt)
            return dt if dt.tzinfo else dt.replace(tzinfo=UTC)
        except Exception:
            continue
    return None


def age_minutes(dt: datetime, ref: datetime | None = None) -> float:
    ref = ref or now_utc()
    return (ref - dt).total_seconds() / 60.0


def human_age(dt: datetime, ref: datetime | None = None) -> str:
    """'14 min ago', '3 hrs ago', 'Sep 14' — the timestamp a reader sees."""
    ref = ref or now_utc()
    mins = (ref - dt).total_seconds() / 60.0
    if mins < 1:
        return "just now"
    if mins < 60:
        return "%d min ago" % int(mins)
    hours = mins / 60.0
    if hours < 24:
        n = int(hours)
        return "1 hr ago" if n == 1 else "%d hrs ago" % n
    days = hours / 24.0
    if days < 7:
        n = int(days)
        return "1 day ago" if n == 1 else "%d days ago" % n
    return dt.astimezone(PACIFIC).strftime("%b %-d")


# --------------------------------------------------------------------------
# JSON read / write
# --------------------------------------------------------------------------
def read_json(path: str, default=None):
    full = path if os.path.isabs(path) else os.path.join(ROOT, path)
    try:
        with open(full, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except FileNotFoundError:
        return default
    except json.JSONDecodeError as exc:
        # Never silently continue on a corrupt data file — that is how a
        # chart history quietly turns into fiction.
        raise SystemExit("FATAL: %s is not valid JSON: %s" % (full, exc))


def write_json(path: str, payload) -> None:
    full = path if os.path.isabs(path) else os.path.join(ROOT, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    tmp = full + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    os.replace(tmp, full)  # atomic: never leaves a half-written data file


def write_text(path: str, text: str) -> None:
    full = path if os.path.isabs(path) else os.path.join(ROOT, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    tmp = full + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(text)
    os.replace(tmp, full)


# --------------------------------------------------------------------------
# HTTP
# --------------------------------------------------------------------------
def fetch(url: str, timeout: int = 20, max_bytes: int = 4_000_000):
    """
    Fetch a URL. Returns (bytes, final_url) or (None, error_string).

    Never raises. A news wire that crashes because one publisher is having a
    bad afternoon is a broken news wire.
    """
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": UA,
            "Accept": "application/rss+xml, application/xml, text/xml, text/html;q=0.9, */*;q=0.8",
            "Accept-Encoding": "gzip",
            "Accept-Language": "en-US,en;q=0.9",
        },
    )
    try:
        ctx = ssl.create_default_context()
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            raw = resp.read(max_bytes)
            if resp.headers.get("Content-Encoding") == "gzip":
                try:
                    raw = gzip.GzipFile(fileobj=io.BytesIO(raw)).read()
                except Exception:
                    pass
            return raw, resp.geturl()
    except urllib.error.HTTPError as exc:
        return None, "HTTP %s" % exc.code
    except urllib.error.URLError as exc:
        return None, "URL error: %s" % exc.reason
    except Exception as exc:  # timeouts, bad TLS, malformed redirects
        return None, "%s: %s" % (type(exc).__name__, exc)


# --------------------------------------------------------------------------
# Feed parsing (RSS 2.0 and Atom), standard library only
# --------------------------------------------------------------------------
NS = {
    "media": "http://search.yahoo.com/mrss/",
    "content": "http://purl.org/rss/1.0/modules/content/",
    "dc": "http://purl.org/dc/elements/1.1/",
    "atom": "http://www.w3.org/2005/Atom",
}

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def strip_html(text: str, limit: int = 320) -> str:
    """Turn a chunk of feed HTML into clean plain text for a card summary."""
    if not text:
        return ""
    text = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", text)
    text = _TAG_RE.sub(" ", text)
    text = _html.unescape(text)
    text = _WS_RE.sub(" ", text).strip()
    if len(text) > limit:
        cut = text[:limit].rsplit(" ", 1)[0]
        text = cut.rstrip(".,;:—-") + "…"
    return text


def _text(el) -> str:
    return (el.text or "").strip() if el is not None else ""


def _localname(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def parse_feed(raw: bytes) -> tuple[list[dict], str | None]:
    """
    Parse RSS or Atom into a list of plain dictionaries.

    Returns (entries, error). Each entry carries the raw pieces the photo
    extractor needs; it does NOT decide anything editorial.
    """
    if not raw:
        return [], "empty response"
    try:
        # Feeds in the wild contain stray control characters that kill a
        # strict XML parser. Scrub the few that are never legal.
        cleaned = re.sub(rb"[\x00-\x08\x0b\x0c\x0e-\x1f]", b"", raw)
        root = ET.fromstring(cleaned)
    except ET.ParseError as exc:
        return [], "not valid XML: %s" % exc

    entries: list[dict] = []
    nodes = root.findall(".//item")
    kind = "rss"
    if not nodes:
        nodes = root.findall(".//{http://www.w3.org/2005/Atom}entry")
        kind = "atom"
    if not nodes:
        return [], "no <item> or <entry> elements found"

    for node in nodes:
        e: dict = {}
        if kind == "rss":
            e["title"] = _html.unescape(_text(node.find("title")))
            e["link"] = _text(node.find("link"))
            e["summary_html"] = _text(node.find("description"))
            e["published_raw"] = (
                _text(node.find("pubDate"))
                or _text(node.find("{http://purl.org/dc/elements/1.1/}date"))
            )
            src = node.find("source")
            if src is not None:
                # Google News puts the real outlet name here.
                e["origin_name"] = (src.text or "").strip()
                e["origin_url"] = src.attrib.get("url", "")
        else:
            e["title"] = _html.unescape(
                _text(node.find("{http://www.w3.org/2005/Atom}title"))
            )
            link_el = node.find(
                "{http://www.w3.org/2005/Atom}link[@rel='alternate']"
            )
            if link_el is None:
                link_el = node.find("{http://www.w3.org/2005/Atom}link")
            e["link"] = link_el.attrib.get("href", "") if link_el is not None else ""
            e["summary_html"] = _text(
                node.find("{http://www.w3.org/2005/Atom}summary")
            ) or _text(node.find("{http://www.w3.org/2005/Atom}content"))
            e["published_raw"] = _text(
                node.find("{http://www.w3.org/2005/Atom}published")
            ) or _text(node.find("{http://www.w3.org/2005/Atom}updated"))

        e["content_html"] = _text(
            node.find("{http://purl.org/rss/1.0/modules/content/}encoded")
        )

        # --- everything the photo chain might use, collected but not judged ---
        media: list[tuple[str, str]] = []  # (kind, url)
        for mc in node.findall("{http://search.yahoo.com/mrss/}content"):
            url = mc.attrib.get("url")
            mtype = mc.attrib.get("medium") or mc.attrib.get("type") or ""
            if url and ("image" in mtype or not mtype):
                media.append(("media:content", url))
        for mt in node.findall("{http://search.yahoo.com/mrss/}thumbnail"):
            if mt.attrib.get("url"):
                media.append(("media:thumbnail", mt.attrib["url"]))
        # media:group wraps the above on some feeds (YouTube does this)
        for grp in node.findall("{http://search.yahoo.com/mrss/}group"):
            for mt in grp.findall("{http://search.yahoo.com/mrss/}thumbnail"):
                if mt.attrib.get("url"):
                    media.append(("media:thumbnail", mt.attrib["url"]))
        for enc in node.findall("enclosure"):
            url = enc.attrib.get("url")
            if url and "image" in (enc.attrib.get("type") or "image"):
                media.append(("enclosure", url))
        e["media"] = media

        cats = []
        for c in node.findall("category"):
            if c.text:
                cats.append(c.text.strip())
        e["categories"] = cats

        if e.get("title") and e.get("link"):
            entries.append(e)

    return entries, None


# --------------------------------------------------------------------------
# PHOTO EXTRACTION — the most important part of the wire.
#
# We hotlink the publisher's own image and credit the publisher under it. That
# is the standard aggregation model (Google News, Flipboard). We never
# download it, never re-host it, never crop out a credit, never watermark it.
# --------------------------------------------------------------------------
_IMG_SRC_RE = re.compile(r"""<img[^>]+?src\s*=\s*["']([^"']+)["']""", re.I)
_OG_RE = re.compile(
    r"""<meta[^>]+?(?:property|name)\s*=\s*["'](?:og:image(?::url)?|twitter:image(?::src)?)["'][^>]*?>""",
    re.I,
)
_CONTENT_RE = re.compile(r"""content\s*=\s*["']([^"']+)["']""", re.I)

# Tracking pixels, spacers, share buttons, avatars — not story photos.
_IMG_REJECT = re.compile(
    r"(doubleclick|googlesyndication|/pixel|pixel\.|1x1|spacer|blank\.gif"
    r"|feedburner|feedsportal|gravatar|/avatar|button|badge|/emoji/"
    r"|share|facebook\.com/tr|scorecardresearch|stats\.wordpress)",
    re.I,
)


def _plausible_image(url: str) -> bool:
    if not url or len(url) < 12:
        return False
    if not url.lower().startswith(("http://", "https://")):
        return False
    if _IMG_REJECT.search(url):
        return False
    return True


def _first_img(html_text: str) -> str | None:
    if not html_text:
        return None
    for m in _IMG_SRC_RE.finditer(_html.unescape(html_text)):
        url = m.group(1).strip()
        if _plausible_image(url):
            return url
    return None


def extract_image(entry: dict, allow_page_fetch: bool = False) -> dict | None:
    """
    Find a photo for a story, in the exact priority order the brief sets:

      1. media:content url=
      2. media:thumbnail url=
      3. enclosure url=
      4. first <img> in content:encoded
      5. first <img> in description
      6. the article page's og:image   (costs a page fetch, so it is last
                                        and is rate-limited by the caller)

    Returns {"url":..., "via":...} or None. Returning None is a legitimate,
    designed outcome: the renderer then draws a text-forward card. It must
    never fall back to a grey box or a stock photo.
    """
    order = {"media:content": 0, "media:thumbnail": 1, "enclosure": 2}
    ranked = sorted(
        [m for m in entry.get("media", []) if _plausible_image(m[1])],
        key=lambda m: order.get(m[0], 9),
    )
    if ranked:
        return {"url": ranked[0][1], "via": ranked[0][0]}

    url = _first_img(entry.get("content_html", ""))
    if url:
        return {"url": url, "via": "content:encoded"}

    url = _first_img(entry.get("summary_html", ""))
    if url:
        return {"url": url, "via": "description"}

    if allow_page_fetch and entry.get("link"):
        raw, final = fetch(entry["link"], timeout=12, max_bytes=900_000)
        if raw:
            try:
                head = raw[:400_000].decode("utf-8", errors="ignore")
            except Exception:
                head = ""
            for tag in _OG_RE.finditer(head):
                cm = _CONTENT_RE.search(tag.group(0))
                if not cm:
                    continue
                candidate = _html.unescape(cm.group(1).strip())
                if candidate.startswith("//"):
                    candidate = "https:" + candidate
                elif candidate.startswith("/"):
                    base = final if isinstance(final, str) else entry["link"]
                    candidate = urllib.parse.urljoin(base, candidate)
                if _plausible_image(candidate):
                    return {"url": candidate, "via": "og:image"}
    return None


# --------------------------------------------------------------------------
# Identity and de-duplication
# --------------------------------------------------------------------------
def story_id(link: str) -> str:
    return hashlib.sha1(link.encode("utf-8", "ignore")).hexdigest()[:16]


_NORM_RE = re.compile(r"[^a-z0-9 ]+")


def title_key(title: str) -> str:
    """
    A loose fingerprint so the same story arriving from five Google News
    queries appears on the page once.
    """
    t = _html.unescape(title or "").lower()
    t = re.sub(r"\s+-\s+[^-]{2,40}$", "", t)  # strip " - Outlet" suffix
    t = _NORM_RE.sub(" ", t)
    t = _WS_RE.sub(" ", t).strip()
    return " ".join(t.split()[:11])


def clean_google_title(title: str) -> tuple[str, str | None]:
    """
    Google News appends ' - Outlet' to every headline. Return the clean
    headline and the outlet name it named.
    """
    m = re.match(r"^(.*?)\s+-\s+([^-]{2,60})$", title or "")
    if m:
        return m.group(1).strip(), m.group(2).strip()
    return (title or "").strip(), None


def esc(text) -> str:
    """Escape text for safe insertion into HTML."""
    return _html.escape(str(text if text is not None else ""), quote=True)


# --------------------------------------------------------------------------
# EDITORIAL RELEVANCE
#
# Why this exists: the wire is sorted newest-first, which means whichever
# publisher posts most often takes the lead slot. One of our verified trade
# feeds also carries general showbusiness, so the front page led with
# "Merriam-Webster Just Made Rickrolling Official" on a gospel news wire.
#
# The fix is RANKING, not deletion. Nothing is thrown away and nothing is
# hidden — the full wire on news.html stays in pure date order, exactly as it
# arrived. This score only decides what leads the FRONT page, the way a
# front-page editor decides what goes above the fold.
# --------------------------------------------------------------------------

# Words that mean a story is squarely about faith, the church, or gospel music.
_FAITH_STRONG = re.compile(
    r"(?i)\b("
    r"church|churches|pastor\w*|gospel|christian\w*|christ|jesus|worship|"
    r"faith|bible|biblical|scripture|ministr\w*|congregat\w*|revival|"
    r"preach\w*|sermon|clergy|bishop|archbishop|cardinal|pope|vatican|"
    r"baptist|methodist|pentecostal|catholic|evangel\w*|missionar\w*|"
    r"theolog\w*|seminary|denominat\w*|parish|diocese|megachurch|"
    r"praise|hymn|choir|psalm|prayer|praying|discipleship|salvation|"
    r"dove awards|stellar awards|ccm|worshipper|anointed|testimony"
    r")\b"
)

# Signals that a story is general showbusiness rather than faith news.
_SECULAR = re.compile(
    r"(?i)\b("
    r"box office|spider-man|star wars|marvel|netflix series|"
    r"rickroll\w*|meatloaf|ponzi|residential treatment|"
    r"semifinals|reality show|dating rumou?rs|red carpet"
    r")\b"
)


def relevance(story: dict, artist_names: set | None = None) -> int:
    """
    Score a story for the FRONT page only. Higher means more clearly a gospel,
    Christian or faith story.

      3  a gospel/Christian music story, or a named gospel artist
      2  clearly a faith or church story
      1  from a dedicated faith publication, topic not obvious from the words
      0  no faith signal we can see

    This never deletes anything. See the note above.
    """
    text = "%s %s" % (story.get("title") or "", story.get("summary") or "")
    cat = story.get("category") or ""

    if artist_names:
        low = text.lower()
        for name in artist_names:
            if name and name.lower() in low:
                return 3

    if cat in ("gospel", "christian-music", "gospel-trade", "artist"):
        if _FAITH_STRONG.search(text):
            return 3
        if _SECULAR.search(text):
            return 0
        return 1

    if _FAITH_STRONG.search(text):
        return 2
    if _SECULAR.search(text):
        return 0

    # A story can be squarely about the church and contain none of the words
    # above — "Robert Morris pleads guilty", "Mother Emanuel Memorial". What
    # makes those on-topic is WHERE THEY CAME FROM:
    #   - a Tier 1 Google News query, every one of which is faith-targeted
    #     ("Black church", "megachurch", "gospel music", a gospel artist), so
    #     the query itself guarantees the subject; or
    #   - a Tier 2 outlet, which is a faith publication by definition.
    # Trusting the source here is what stops real church news being pushed off
    # the front page just because the headline used none of our words.
    if story.get("tier") in (1, 2):
        return 1
    return 0


def gospel_artist_names() -> set:
    """The real, public artist names already listed in data/news-sources.json."""
    doc = read_json("data/news-sources.json", {}) or {}
    names = set()
    for s in doc.get("sources", []):
        if s.get("category") == "artist" and s.get("name", "").startswith("Google News: "):
            names.add(s["name"].replace("Google News: ", "").strip())
    return names
