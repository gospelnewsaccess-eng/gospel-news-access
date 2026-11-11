"""
layout.py — the parts of the page that are the same everywhere.

Plain English: the header, the navigation bar, the footer, a story card, the
breaking banner. Every page calls these, so the site looks like one publication
instead of fourteen loose documents. Change the nav here and it changes on
every page at once.
"""

from __future__ import annotations

import sys

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import gnalib as g  # noqa: E402

SITE = g.SITE_URL
NAME = g.SITE_NAME
TAGLINE = "Gospel, Christian and faith news — updated continuously"

# label, href (relative to site root), nav key
NAV = [
    ("Front Page", "index.html", "home"),
    ("News", "news.html", "news"),
    ("Music", "music.html", "music"),
    ("Charts", "charts.html", "charts"),
    ("Video", "video.html", "video"),
    ("CDC", "cdc/index.html", "cdc"),
    ("Churches", "churches.html", "churches"),
    ("Submit Music", "submit-music.html", "submit"),
    ("About", "about.html", "about"),
]


def rel(depth: int, path: str) -> str:
    """Build a link that works from a page nested `depth` folders deep."""
    return ("../" * depth) + path


def head(title: str, description: str, canonical: str, depth: int = 0,
         schema_blocks: list[str] | None = None, image: str | None = None,
         page_type: str = "WebPage") -> str:
    """
    The <head> of every page: what it is called, what it is about, how it
    looks when shared, and the machine-readable description search engines
    read (JSON-LD).
    """
    css = rel(depth, "assets/css/gna.css")
    full_title = title if title.startswith(NAME) else "%s — %s" % (title, NAME)
    og_image = image or ""
    blocks = "\n".join(schema_blocks or [])
    og_img_tags = ""
    if og_image:
        og_img_tags = (
            '\n<meta property="og:image" content="%s">'
            '\n<meta name="twitter:image" content="%s">' % (g.esc(og_image), g.esc(og_image))
        )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{g.esc(full_title)}</title>
<meta name="description" content="{g.esc(description)}">
<link rel="canonical" href="{g.esc(canonical)}">
<meta name="robots" content="index, follow, max-image-preview:large, max-snippet:-1">

<meta property="og:type" content="website">
<meta property="og:site_name" content="{g.esc(NAME)}">
<meta property="og:title" content="{g.esc(full_title)}">
<meta property="og:description" content="{g.esc(description)}">
<meta property="og:url" content="{g.esc(canonical)}">{og_img_tags}
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{g.esc(full_title)}">
<meta name="twitter:description" content="{g.esc(description)}">

<link rel="stylesheet" href="{css}">
<link rel="alternate" type="application/rss+xml" title="{g.esc(NAME)}" href="{rel(depth,'feed.xml')}">
{blocks}
</head>
<body>
<a class="skip" href="#main">Skip to main content</a>
"""


def breaking_banner(stories: list[dict], depth: int = 0) -> str:
    """
    THE KILL SWITCH.

    Every story carries breaking_expires_at, written 12 hours after we first
    saw it. This function checks that expiry against the clock on every single
    page build. An expired flag renders nothing at all — no banner, no tag.
    That is why a stale BREAKING banner cannot survive here: it is not
    something a person has to remember to take down.
    """
    now = g.now_utc()
    live = [
        s for s in stories
        if s.get("breaking")
        and s.get("breaking_expires_at")
        and (g.parse_dt(s["breaking_expires_at"]) or now) > now
    ]
    if not live:
        return ""
    live.sort(key=lambda s: s["published"], reverse=True)
    s = live[0]
    return f"""<div class="breaking">
  <div class="wrap">
    <span class="breaking__tag">Breaking</span>
    <span class="breaking__hd"><a href="{g.esc(s['link'])}" rel="noopener">{g.esc(s['title'])}</a></span>
  </div>
</div>
"""


def header(depth: int = 0) -> str:
    today = g.now_pacific().strftime("%A, %B %-d, %Y")
    return f"""<header class="masthead">
  <div class="wrap">
    <p class="logo"><a href="{rel(depth,'index.html')}">Gospel News Access<span class="dot">.</span></a></p>
    <p class="masthead__meta">{g.esc(today)} &middot; Updated continuously</p>
  </div>
</header>
"""


def nav(current: str, depth: int = 0) -> str:
    links = []
    for label, href, key in NAV:
        cur = ' aria-current="page"' if key == current else ""
        links.append('<a href="%s"%s>%s</a>' % (rel(depth, href), cur, g.esc(label)))
    return ('<nav class="nav" aria-label="Sections"><div class="wrap">'
            '<div class="nav__inner">%s</div></div></nav>\n' % "".join(links))


# Social icons + network links band above the footer on every page.
FOLLOW_BAND = '<!-- FOLLOW:START -->\n<style>section.sf{padding:0;margin:0;min-height:0}.sf .sf-h,.sf .sf-t{margin:0}.sf .sf-h{margin-bottom:6px}.sf{background:#0D0D0F;color:#F3F0EA;border-top:3px solid #E0B341;font-family:Inter,system-ui,sans-serif}.sf-w{max-width:1240px;margin:0 auto;padding:30px 18px 26px;display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:20px 40px}.sf-h{font-weight:800;font-size:13px;letter-spacing:.22em;text-transform:uppercase;color:#fff;margin:0 0 6px}.sf-h b{color:#E0B341}.sf-t{font-size:14px;color:#A9A39A;margin:0}.sf-row{display:flex;gap:12px;flex-wrap:wrap}.sf-i{width:46px;height:46px;border-radius:50%;display:inline-flex;align-items:center;justify-content:center;border:1.5px solid rgba(255,255,255,.35);color:#fff;transition:background .2s,border-color .2s,transform .2s}.sf-i svg{width:21px;height:21px}.sf-i:hover,.sf-i:focus-visible{background:#E0B341;border-color:#E0B341;color:#0A0A0A;transform:translateY(-2px)}.sf-net{flex-basis:100%;display:flex;flex-wrap:wrap;gap:8px 22px;align-items:center;border-top:1px solid rgba(255,255,255,.12);padding-top:16px;font-size:13px;font-weight:600;letter-spacing:.06em}.sf-net span{text-transform:uppercase;letter-spacing:.2em;font-size:11px;color:#8C867D}.sf-net a{color:#E9E4DA;text-decoration:none}.sf-net a:hover{color:#E0B341}.sf-net a[aria-current]{color:#E0B341}@media (prefers-reduced-motion:reduce){.sf-i{transition:none}}</style>\n<section class="sf" aria-label="Follow Gospel News Access"><div class="sf-w"><div><p class="sf-h">Follow <b>Gospel News Access</b></p><p class="sf-t">Gospel music, faith leaders and good news, every day.</p></div><div class="sf-row"><a class="sf-i" href="https://www.facebook.com/profile.php?id=100069397881039" target="_blank" rel="noopener me" aria-label="Gospel News Access on Facebook" title="Facebook"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M13.5 21v-7.5h2.6l.4-3h-3V8.6c0-.9.3-1.5 1.6-1.5h1.6V4.4c-.3 0-1.2-.1-2.3-.1-2.3 0-3.9 1.4-3.9 4v2.2H7.9v3h2.6V21h3z" fill="currentColor"/></svg></a><a class="sf-i" href="https://www.instagram.com/gospelnewsaccess/" target="_blank" rel="noopener me" aria-label="Gospel News Access on Instagram" title="Instagram"><svg viewBox="0 0 24 24" aria-hidden="true"><rect x="3.5" y="3.5" width="17" height="17" rx="5" fill="none" stroke="currentColor" stroke-width="2"/><circle cx="12" cy="12" r="4" fill="none" stroke="currentColor" stroke-width="2"/><circle cx="17.3" cy="6.7" r="1.2" fill="currentColor"/></svg></a><a class="sf-i" href="https://www.threads.net/@gospelnewsaccess" target="_blank" rel="noopener me" aria-label="Gospel News Access on Threads" title="Threads"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M16.6 11.2c-.1 0-.2-.1-.3-.1-.2-3-1.9-4.7-4.6-4.7h-.1c-1.6 0-3 .7-3.8 2l1.5 1c.6-.9 1.6-1.1 2.3-1.1h.1c.9 0 1.6.3 2 .8.3.4.5.9.6 1.6-.8-.1-1.6-.2-2.5-.1-2.5.1-4.1 1.6-4 3.6.1 1 .6 1.9 1.4 2.5.7.5 1.6.7 2.6.6 1.3-.1 2.3-.6 3-1.5.5-.7.9-1.6 1-2.7.6.4 1.1.9 1.3 1.5.4 1 .4 2.6-.9 3.9-1.1 1.1-2.5 1.6-4.5 1.6-2.2 0-3.9-.7-5-2.1C5.6 16.6 5 14.6 5 12s.6-4.6 1.7-6C7.8 4.6 9.5 3.9 11.7 3.9s4 .7 5.1 2.1c.6.7 1 1.5 1.3 2.5l1.8-.5c-.4-1.3-.9-2.4-1.7-3.3C16.6 2.9 14.4 2 11.7 2h-.1C8.9 2 6.8 2.9 5.3 4.7 4 6.3 3.3 8.8 3.3 12s.7 5.7 2 7.3C6.8 21.1 8.9 22 11.6 22h.1c2.4 0 4.1-.6 5.5-2 1.9-1.9 1.8-4.2 1.2-5.7-.4-1-1.3-1.9-2.4-2.4l.6-.7zm-4.3 4.6c-1 .1-2.1-.4-2.1-1.4 0-.7.5-1.6 2.4-1.7h.6c.7 0 1.3.1 1.9.2-.2 2.4-1.5 2.8-2.8 2.9z" fill="currentColor"/></svg></a><a class="sf-i" href="https://www.youtube.com/@gospelnewsaccesschannel" target="_blank" rel="noopener me" aria-label="Gospel News Access on YouTube" title="YouTube"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M21.6 7.2a2.6 2.6 0 0 0-1.8-1.8C18.2 5 12 5 12 5s-6.2 0-7.8.4A2.6 2.6 0 0 0 2.4 7.2C2 8.8 2 12 2 12s0 3.2.4 4.8a2.6 2.6 0 0 0 1.8 1.8C5.8 19 12 19 12 19s6.2 0 7.8-.4a2.6 2.6 0 0 0 1.8-1.8c.4-1.6.4-4.8.4-4.8s0-3.2-.4-4.8zM10 15V9l5.2 3L10 15z" fill="currentColor"/></svg></a></div><div class="sf-net"><span>Our network</span><a href="https://newswirehollywood.com/">Newswire Hollywood</a><a href="https://hollywoodnewsaccess.com/">Hollywood News Access</a><a href="https://gospelnewsaccess.com/" aria-current="page">Gospel News Access</a><a href="https://prstarpower.com/">PR STARPOWER</a></div></div></section>\n<!-- FOLLOW:END -->\n'


def footer(depth: int = 0) -> str:
    year = g.now_pacific().year
    r = lambda p: rel(depth, p)  # noqa: E731
    return FOLLOW_BAND + f"""<footer class="foot">
  <div class="wrap">
    <div class="foot__cols">
      <div>
        <h4>Sections</h4>
        <ul>
          <li><a href="{r('news.html')}">News Wire</a></li>
          <li><a href="{r('music.html')}">Music</a></li>
          <li><a href="{r('charts.html')}">GNA Charts</a></li>
          <li><a href="{r('video.html')}">Video</a></li>
          <li><a href="{r('churches.html')}">Church Directory</a></li>
        </ul>
      </div>
      <div>
        <h4>The Charts</h4>
        <ul>
          <li><a href="{r('charts/methodology.html')}">Chart Methodology</a></li>
          <li><a href="{r('charts/panel.html')}">Reporter Panel</a></li>
          <li><a href="{r('submit-music.html')}">Submit Music</a></li>
        </ul>
      </div>
      <div>
        <h4>Community</h4>
        <ul>
          <li><a href="{r('cdc/index.html')}">Community Development</a></li>
          <li><a href="{r('cdc/gospel-news-access/index.html')}">Gospel News Access CDC</a></li>
          <li><a href="{r('cdc/his-presence-fire/index.html')}">His Presence Fire CDC</a></li>
          <li><a href="{r('churches/join.html')}">Add Your Church</a></li>
        </ul>
      </div>
      <div>
        <h4>The Publication</h4>
        <ul>
          <li><a href="{r('about.html')}">About &amp; Ownership</a></li>
          <li><a href="{r('masthead.html')}">Masthead</a></li>
          <li><a href="{r('pressroom.html')}">Press Room</a></li>
          <li><a href="{r('contact.html')}">Contact</a></li>
          <li><a href="{r('corrections.html')}">Corrections Policy</a></li>
          <li><a href="{r('privacy.html')}">Privacy</a></li>
          <li><a href="https://www.instagram.com/gospelnewsaccess/" target="_blank" rel="noopener me">Instagram</a></li>
          <li><a href="https://www.facebook.com/profile.php?id=100069397881039" target="_blank" rel="noopener me">Facebook</a></li>
        </ul>
      </div>
    </div>
    <div class="foot__legal">
      <p><strong>Gospel News Access</strong> is an independent gospel, Christian and
      faith news wire. Headlines on the wire link to the publication that reported
      them; photographs are displayed from the original publisher and credited to
      them. Copyright in that material remains with its owner.</p>
      <p>Gospel News Access does not accept payment for news coverage, for chart
      consideration, or for chart position. See our
      <a href="{r('charts/methodology.html')}">chart methodology</a> and
      <a href="{r('corrections.html')}">corrections policy</a>.</p>
      <p>&copy; {year} Gospel News Access. Page built {g.esc(g.now_pacific().strftime('%b %-d, %Y at %-I:%M %p'))} Pacific.</p>
    </div>
  </div>
</footer>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Story cards
# ---------------------------------------------------------------------------
def _byline(story: dict, now) -> str:
    published = g.parse_dt(story["published"]) or now
    bits = []
    live_breaking = (
        story.get("breaking")
        and story.get("breaking_expires_at")
        and (g.parse_dt(story["breaking_expires_at"]) or now) > now
    )
    if live_breaking:
        bits.append('<span class="tag tag--breaking">Breaking</span>')
    bits.append('<span class="byline__src">%s</span>' % g.esc(story.get("outlet") or "Wire"))
    bits.append('<span class="byline__dot">&bull;</span>')
    bits.append("<time datetime=\"%s\">%s</time>" % (g.esc(story["published"]), g.esc(g.human_age(published, now))))
    return '<p class="byline">%s</p>' % "".join(bits)


def _photo_credit(story: dict) -> str:
    """Who to name under a wire photo. It is always the outlet whose photograph
    it is - never Gospel News Access - and a YouTube thumbnail says so."""
    img = story.get("image") or {}
    who = (story.get("outlet") or story.get("source_feed") or "the publisher").strip()
    if img.get("via") == "youtube":
        return "Thumbnail: YouTube"
    return "Photo: %s" % who


def card(story: dict, now=None) -> str:
    """
    One story on the grid.

    If we found a photo we show the publisher's own image and credit them
    under it. If we did not, we render a TEXT-FORWARD card — bigger headline,
    a rule down the side. Never a grey box. Never a stock photo standing in
    for a picture we do not have.
    """
    now = now or g.now_utc()
    img = story.get("image")
    link = g.esc(story["link"])
    title = g.esc(story["title"])
    dek = ('<p class="card__dek">%s</p>' % g.esc(story["summary"])) if story.get("summary") else ""

    if img:
        return f"""<article class="card">
  <figure class="card__fig"><a href="{link}" rel="noopener" target="_blank"><img src="{g.esc(img['url'])}" alt="" loading="lazy" referrerpolicy="no-referrer"></a><figcaption class="card__credit">{g.esc(_photo_credit(story))}</figcaption></figure>
  <h3 class="card__hd"><a href="{link}" rel="noopener" target="_blank">{title}</a></h3>
  {dek}
  {_byline(story, now)}
</article>
"""
    return f"""<article class="card card--text">
  <h3 class="card__hd"><a href="{link}" rel="noopener" target="_blank">{title}</a></h3>
  {dek}
  {_byline(story, now)}
</article>
"""


def original_card(article: dict, depth: int = 0, now=None) -> str:
    """
    One piece of OUR OWN reporting on a grid.

    Deliberately not the same as card(): a wire card links out to the
    publisher that wrote the story and opens in a new tab. This links inward,
    in the same tab, and the byline says Gospel News Access rather than a
    third-party outlet. Originals carry no image unless we hold a licence for
    one, so this always renders text-forward.
    """
    now = now or g.now_utc()
    published = g.parse_dt(article["published"]) or now
    link = rel(depth, "story/%s.html" % article["slug"])
    dek = ('<p class="card__dek">%s</p>' % g.esc(article["standfirst"])) if article.get("standfirst") else ""
    return f"""<article class="card card--text">
  <h3 class="card__hd"><a href="{g.esc(link)}">{g.esc(article['title'])}</a></h3>
  {dek}
  <p class="byline"><span class="byline__src">Gospel News Access</span><span class="byline__dot">&bull;</span><time datetime="{g.esc(article['published'])}">{g.esc(g.human_age(published, now))}</time></p>
</article>
"""


def hero(story: dict, now=None) -> str:
    now = now or g.now_utc()
    img = story.get("image")
    link = g.esc(story["link"])
    title = g.esc(story["title"])
    dek = ('<p class="hero__dek">%s</p>' % g.esc(story["summary"])) if story.get("summary") else ""
    if img:
        credit = "Photo: %s" % g.esc(story.get("outlet") or "original publisher")
        return f"""<article class="hero">
  <figure class="hero__fig">
    <a href="{link}" rel="noopener" target="_blank"><img src="{g.esc(img['url'])}" alt="" referrerpolicy="no-referrer"></a>
    <figcaption class="hero__credit">{credit}</figcaption>
  </figure>
  <div>
    <h2 class="hero__hd"><a href="{link}" rel="noopener" target="_blank">{title}</a></h2>
    {dek}
    {_byline(story, now)}
  </div>
</article>
"""
    return f"""<article class="hero hero--text">
  <div>
    <h2 class="hero__hd"><a href="{link}" rel="noopener" target="_blank">{title}</a></h2>
    {dek}
    {_byline(story, now)}
  </div>
</article>
"""


def srule(label: str, more_href: str | None = None, more_label: str = "See all") -> str:
    more = ('<a class="more" href="%s">%s &rarr;</a>' % (g.esc(more_href), g.esc(more_label))) if more_href else ""
    return '<div class="srule"><h2>%s</h2>%s</div>\n' % (g.esc(label), more)


def empty(heading: str, body_html: str) -> str:
    """An honest empty state. Used where there is genuinely nothing yet."""
    return '<div class="empty"><h3>%s</h3>%s</div>\n' % (g.esc(heading), body_html)


def breadcrumbs(trail: list[tuple[str, str]]) -> str:
    """BreadcrumbList JSON-LD — tells search engines how sections nest."""
    items = []
    for i, (name, url) in enumerate(trail, start=1):
        items.append(
            '{"@type":"ListItem","position":%d,"name":%s,"item":%s}'
            % (i, _js(name), _js(url))
        )
    return ('<script type="application/ld+json">'
            '{"@context":"https://schema.org","@type":"BreadcrumbList","itemListElement":[%s]}'
            "</script>" % ",".join(items))


def _js(value) -> str:
    import json
    return json.dumps(value if value is not None else "", ensure_ascii=False)
