#!/usr/bin/env python3
"""
render_site.py — turns stored data into the actual website.

Plain English: the other scripts go and FETCH things. This one takes what they
fetched and writes the HTML files a browser opens. It is the only script that
writes a .html file, so every page is guaranteed the same header, the same
navigation and the same footer.

It is safe to run at any time. It never fetches anything and never invents
anything: if a piece of data is missing, the block that would have shown it is
left out entirely.

Usage:  python3 scripts/render_site.py
"""

from __future__ import annotations

import json
import os
import sys
from datetime import timedelta

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import gnalib as g          # noqa: E402
import layout as L          # noqa: E402

SITE = g.SITE_URL
HERO_MAX_AGE_HOURS = 72


def _js(v) -> str:
    return json.dumps(v if v is not None else "", ensure_ascii=False)


def cfg() -> dict:
    return g.read_json("data/site-config.json", {}) or {}


def stories() -> list[dict]:
    doc = g.read_json("data/articles.json", {"items": []}) or {"items": []}
    items = doc.get("items", [])
    items.sort(key=lambda s: s.get("published", ""), reverse=True)
    return items


def live_breaking(items, now):
    return [
        s for s in items
        if s.get("breaking") and s.get("breaking_expires_at")
        and (g.parse_dt(s["breaking_expires_at"]) or now) > now
    ]


# ---------------------------------------------------------------------------
# Structured data (the machine-readable description search engines read)
# ---------------------------------------------------------------------------
def org_schema() -> str:
    """
    NewsMediaOrganization — tells Google this is a news publisher, who owns it
    and where to find its policies. This is the block that supports E-E-A-T.
    """
    c = cfg().get("organization", {})
    obj = {
        "@context": "https://schema.org",
        "@type": "NewsMediaOrganization",
        "name": c.get("name", "Gospel News Access"),
        "url": SITE + "/",
        "description": "An independent gospel, Christian and faith news wire.",
        "ethicsPolicy": SITE + "/corrections.html",
        "correctionsPolicy": SITE + "/corrections.html",
        "masthead": SITE + "/masthead.html",
        "publishingPrinciples": SITE + "/about.html",
    }
    # Only real, supplied facts are ever added.
    if c.get("legal_name"):
        obj["legalName"] = c["legal_name"]
    if c.get("founded_year"):
        obj["foundingDate"] = str(c["founded_year"])
    if c.get("owner_name"):
        obj["founder"] = {"@type": "Person", "name": c["owner_name"]}
    contact = {}
    if c.get("email_general"):
        contact["email"] = c["email_general"]
    if c.get("phone"):
        contact["telephone"] = c["phone"]
    if contact:
        contact["@type"] = "ContactPoint"
        contact["contactType"] = "newsroom"
        obj["contactPoint"] = contact
    sm = [v for v in (cfg().get("social") or {}).values() if isinstance(v, str) and v.startswith("http")]
    if sm:
        obj["sameAs"] = sm
    return '<script type="application/ld+json">%s</script>' % json.dumps(obj, ensure_ascii=False)


def wire_itemlist_schema(items: list[dict], name: str, page_url: str) -> str:
    """
    ItemList — the honest way to describe an aggregated wire.

    NOTE ON A DELIBERATE DEVIATION FROM THE ORIGINAL SPEC:
    The brief asked for NewsArticle JSON-LD on every story. We do NOT do that
    for wire items, and the reason matters. NewsArticle tells Google "this
    publication wrote this article." For a headline that links to Religion
    News Service, that claim is false. Google treats a site that marks up
    other people's reporting as its own as a spam signal, and the penalty
    lands on the whole domain — the exact opposite of search dominance.
    ItemList is the correct, truthful markup for a curated list of links.

    NewsArticle IS used, correctly, on our own original reporting — see
    article_schema() below.
    """
    elements = []
    for i, s in enumerate(items[:30], start=1):
        elements.append({
            "@type": "ListItem",
            "position": i,
            "url": s["link"],
            "name": s["title"],
        })
    obj = {
        "@context": "https://schema.org",
        "@type": "ItemList",
        "name": name,
        "url": page_url,
        "numberOfItems": len(elements),
        "itemListElement": elements,
    }
    return '<script type="application/ld+json">%s</script>' % json.dumps(obj, ensure_ascii=False)


def article_schema(a: dict) -> str:
    """NewsArticle — used ONLY on original reporting that we actually wrote."""
    obj = {
        "@context": "https://schema.org",
        "@type": "NewsArticle",
        "headline": a["title"],
        "datePublished": a["published"],
        "dateModified": a.get("updated") or a["published"],
        "url": "%s/story/%s.html" % (SITE, a["slug"]),
        "mainEntityOfPage": {"@type": "WebPage", "@id": "%s/story/%s.html" % (SITE, a["slug"])},
        "author": {"@type": "Organization", "name": a.get("byline", "Gospel News Access Staff")},
        "publisher": {
            "@type": "NewsMediaOrganization",
            "name": "Gospel News Access",
            "url": SITE + "/",
        },
        "description": a.get("standfirst", ""),
    }
    if a.get("image"):
        obj["image"] = [a["image"]]
    return '<script type="application/ld+json">%s</script>' % json.dumps(obj, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Chart strip (front page) — reads chart history, never a stale week
# ---------------------------------------------------------------------------
def chart_strip(depth: int = 0) -> str:
    hist = g.read_json("data/charts/history.json", {}) or {}
    charts = hist.get("charts", {})
    published = hist.get("last_published")
    if not charts or not published:
        return L.empty(
            "The GNA charts have not published yet",
            '<p>The first chart publishes once the reporter panel and the '
            'submission window have produced a full tracking week. Charts are '
            'published every Tuesday at 12:00 noon Pacific. '
            '<a href="%scharts/methodology.html">Read the methodology</a>.</p>'
            % L.rel(depth, ""),
        )

    def rows(chart_key, limit):
        entries = (charts.get(chart_key) or {}).get("entries", [])[:limit]
        out = []
        for e in entries:
            last = e.get("last_week")
            pos = e.get("current_position")
            if e.get("debut"):
                mv = '<span class="mv mv--new">NEW</span>'
            elif e.get("re_entry"):
                mv = '<span class="mv mv--re">RE</span>'
            elif last is None:
                mv = '<span class="mv mv--same">&ndash;</span>'
            elif last > pos:
                mv = '<span class="mv mv--up">&#9650;%d</span>' % (last - pos)
            elif last < pos:
                mv = '<span class="mv mv--down">&#9660;%d</span>' % (pos - last)
            else:
                mv = '<span class="mv mv--same">&ndash;</span>'
            out.append(
                '<div class="chartrow"><div class="chartrow__pos">%d</div>'
                '<div class="chartrow__t"><span class="chartrow__title">%s</span>'
                '<span class="chartrow__artist">%s</span></div>%s</div>'
                % (pos, g.esc(e.get("title", "")), g.esc(e.get("artist", "")), mv)
            )
        return "".join(out)

    week = g.esc(published)
    g20 = rows("gospel_20", 5)
    hot = rows("whats_hot", 3)
    parts = []
    if g20:
        parts.append(
            '<div class="strip"><div class="strip__hd"><h3>GNA Gospel 20</h3>'
            '<span class="strip__wk">Week of %s</span></div>%s'
            '<p style="margin:12px 0 0"><a class="more" href="%s">Full chart &rarr;</a></p></div>'
            % (week, g20, L.rel(depth, "charts.html"))
        )
    if hot:
        parts.append(
            '<div class="strip"><div class="strip__hd"><h3>What&rsquo;s Hot</h3>'
            '<span class="strip__wk">Fastest movers</span></div>%s'
            '<p style="margin:12px 0 0"><a class="more" href="%s">All 10 &rarr;</a></p></div>'
            % (hot, L.rel(depth, "charts.html"))
        )
    return "".join(parts)


def video_row(depth: int = 0, limit: int = 3) -> str:
    doc = g.read_json("data/videos.json", {"items": []}) or {"items": []}
    items = doc.get("items", [])[:limit]
    if not items:
        return L.empty(
            "The video wall is ready and waiting on its first channel",
            "<p>No YouTube channel has been connected yet. Add one to "
            "<code>data/video-sources.json</code> and videos appear here "
            "automatically within six hours. See "
            "<a href=\"%s\">the video page</a>.</p>" % L.rel(depth, "video.html"),
        )
    cards = []
    for v in items:
        cards.append(
            '<article class="vcard"><div class="vframe">'
            '<iframe src="https://www.youtube-nocookie.com/embed/%s" title="%s" '
            'loading="lazy" allow="accelerometer; clipboard-write; encrypted-media; '
            'gyroscope; picture-in-picture" allowfullscreen></iframe></div>'
            '<div class="vcard__body"><h3 class="vcard__hd">%s</h3>'
            '<p class="byline"><span class="byline__src">%s</span></p></div></article>'
            % (g.esc(v["video_id"]), g.esc(v["title"]), g.esc(v["title"]),
               g.esc(v.get("channel", "")))
        )
    return '<div class="vgrid">%s</div>' % "".join(cards)


# ---------------------------------------------------------------------------
# PAGE: front page
# ---------------------------------------------------------------------------
def render_index() -> None:
    now = g.now_utc()
    items = stories()
    breaking = live_breaking(items, now)

    # THE 72-HOUR HERO RULE. The lead slot must never hold an old story, even
    # if the wire has gone quiet. We prefer a fresh story that has a photo;
    # if none of the fresh stories has one we still lead with a fresh story
    # and render it text-forward rather than leading with something stale.
    fresh_cut = now - timedelta(hours=HERO_MAX_AGE_HOURS)
    fresh = [s for s in items if (g.parse_dt(s["published"]) or now) >= fresh_cut]
    lead = None
    for s in fresh:
        if s.get("image"):
            lead = s
            break
    if lead is None and fresh:
        lead = fresh[0]

    rest = [s for s in items if not lead or s["id"] != lead["id"]]

    if lead:
        hero_html = L.hero(lead, now)
        grid_html = '<div class="grid">%s</div>' % "".join(L.card(s, now) for s in rest[:18])
        desc = g.strip_html(lead.get("summary") or lead["title"], 155)
        og_img = (lead.get("image") or {}).get("url")
    else:
        hero_html = L.empty(
            "The wire has no story fresh enough to lead with",
            "<p>Nothing on the wire was published in the last 72 hours, so the "
            "lead slot is deliberately empty rather than showing you something "
            "stale. The wire checks for new stories every 30 minutes.</p>",
        )
        grid_html = ""
        desc = ("Gospel, Christian and faith news, updated continuously. "
                "Music, the GNA charts, video and community development.")
        og_img = None

    schema = [org_schema()]
    if items:
        schema.append(wire_itemlist_schema(items, "Gospel News Access front page", SITE + "/"))

    html = [
        L.head("Gospel News Access — Gospel, Christian and Faith News Wire",
               desc, SITE + "/", 0, schema, og_img),
        L.breaking_banner(items, 0),
        L.header(0),
        L.nav("home", 0),
        '<main id="main" class="wrap">',
    ]
    if breaking and len(breaking) > 1:
        html.append(L.srule("Breaking"))
        html.append('<div class="grid">%s</div>'
                    % "".join(L.card(s, now) for s in breaking[:3]))

    html.append('<div class="frontsplit"><div>')
    html.append(hero_html)
    if grid_html:
        html.append(L.srule("The Wire", "news.html", "Full wire"))
        html.append(grid_html)
    html.append("</div><aside>")
    html.append(chart_strip(0))
    html.append("</aside></div>")

    html.append(L.srule("Video", "video.html", "Video wall"))
    html.append(video_row(0))

    music = [s for s in items if s.get("category") in ("gospel", "christian-music", "artist", "gospel-trade")]
    if music:
        html.append(L.srule("Music", "music.html", "Music news"))
        html.append('<div class="grid">%s</div>' % "".join(L.card(s, now) for s in music[:6]))

    html.append("</main>")
    html.append(L.footer(0))
    g.write_text("index.html", "".join(html))


# ---------------------------------------------------------------------------
# PAGE: the full wire
# ---------------------------------------------------------------------------
def render_news() -> None:
    now = g.now_utc()
    items = stories()
    crumbs = L.breadcrumbs([("Front Page", SITE + "/"), ("News", SITE + "/news.html")])
    schema = [crumbs]
    if items:
        schema.append(wire_itemlist_schema(items, "Gospel News Access news wire", SITE + "/news.html"))

    html = [
        L.head("News Wire",
               "Every gospel, Christian and faith story on the Gospel News Access "
               "wire, newest first, updated every 30 minutes.",
               SITE + "/news.html", 0, schema),
        L.breaking_banner(items, 0),
        L.header(0),
        L.nav("news", 0),
        '<main id="main" class="wrap">',
        '<h1 class="prose" style="font-family:var(--serif);font-size:34px;margin:22px 0 4px">The Wire</h1>',
    ]
    if items:
        newest = g.parse_dt(items[0]["published"]) or now
        html.append('<p class="dateline">%d stories &middot; newest %s &middot; '
                    'checked every 30 minutes</p>'
                    % (len(items), g.esc(g.human_age(newest, now))))
        by_day: dict[str, list] = {}
        for s in items:
            d = (g.parse_dt(s["published"]) or now).astimezone(g.PACIFIC).strftime("%A, %B %-d")
            by_day.setdefault(d, []).append(s)
        for day, group in list(by_day.items())[:8]:
            html.append(L.srule(day))
            html.append('<div class="grid">%s</div>'
                        % "".join(L.card(s, now) for s in group))
    else:
        html.append(L.empty(
            "The wire has not run yet",
            "<p>No stories have been fetched yet. The wire runs every 30 minutes "
            "on a schedule; the first run fills this page automatically. If this "
            "message is still here after an hour, check that the feeds have been "
            "verified.</p>"))
    html.append("</main>")
    html.append(L.footer(0))
    g.write_text("news.html", "".join(html))


# ---------------------------------------------------------------------------
# PAGE: music
# ---------------------------------------------------------------------------
def render_music() -> None:
    now = g.now_utc()
    items = [s for s in stories()
             if s.get("category") in ("gospel", "christian-music", "artist", "gospel-trade")]
    crumbs = L.breadcrumbs([("Front Page", SITE + "/"), ("Music", SITE + "/music.html")])
    schema = [crumbs]
    if items:
        schema.append(wire_itemlist_schema(items, "Gospel and Christian music news", SITE + "/music.html"))
    html = [
        L.head("Music",
               "Gospel and Christian music news, new releases and artist coverage, "
               "plus the GNA charts.",
               SITE + "/music.html", 0, schema),
        L.breaking_banner(stories(), 0),
        L.header(0),
        L.nav("music", 0),
        '<main id="main" class="wrap">',
        '<h1 class="prose" style="font-family:var(--serif);font-size:34px;margin:22px 0 4px">Music</h1>',
        '<p class="dateline">Gospel and Christian music news, releases and artists</p>',
        chart_strip(0),
    ]
    if items:
        html.append(L.srule("Music News", "news.html", "Full wire"))
        html.append('<div class="grid">%s</div>' % "".join(L.card(s, now) for s in items[:30]))
    else:
        html.append(L.empty(
            "No music stories on the wire yet",
            "<p>Music coverage appears here automatically as soon as the wire "
            "picks it up from the gospel and Christian music trade feeds.</p>"))
    html.append("</main>")
    html.append(L.footer(0))
    g.write_text("music.html", "".join(html))


# ---------------------------------------------------------------------------
# PAGE: video wall
# ---------------------------------------------------------------------------
def render_video() -> None:
    doc = g.read_json("data/videos.json", {"items": []}) or {"items": []}
    items = doc.get("items", [])
    crumbs = L.breadcrumbs([("Front Page", SITE + "/"), ("Video", SITE + "/video.html")])
    schema = [crumbs]

    # VideoObject JSON-LD per video. This — not the embed — is what puts a
    # video thumbnail next to a result in Google.
    for v in items[:40]:
        obj = {
            "@context": "https://schema.org",
            "@type": "VideoObject",
            "name": v["title"],
            "description": v.get("summary") or v["title"],
            "thumbnailUrl": v.get("thumbnail"),
            "uploadDate": v.get("published"),
            "embedUrl": "https://www.youtube-nocookie.com/embed/%s" % v["video_id"],
            "contentUrl": v.get("link"),
            "publisher": {"@type": "Organization", "name": v.get("channel", "")},
        }
        obj = {k: val for k, val in obj.items() if val}
        schema.append('<script type="application/ld+json">%s</script>'
                      % json.dumps(obj, ensure_ascii=False))

    html = [
        L.head("Video",
               "Gospel and Christian video — worship, performance, interviews and "
               "sermons from the channels Gospel News Access follows.",
               SITE + "/video.html", 0, schema),
        L.breaking_banner(stories(), 0),
        L.header(0),
        L.nav("video", 0),
        '<main id="main" class="wrap">',
        '<h1 class="prose" style="font-family:var(--serif);font-size:34px;margin:22px 0 4px">Video</h1>',
    ]
    if items:
        html.append('<p class="dateline">%d videos &middot; refreshed every six hours</p>' % len(items))
        cards = []
        for v in items:
            cards.append(
                '<article class="vcard"><div class="vframe">'
                '<iframe src="https://www.youtube-nocookie.com/embed/%s" title="%s" '
                'loading="lazy" allow="accelerometer; clipboard-write; encrypted-media; '
                'gyroscope; picture-in-picture" allowfullscreen></iframe></div>'
                '<div class="vcard__body"><h3 class="vcard__hd">'
                '<a href="%s" rel="noopener" target="_blank">%s</a></h3>'
                '<p class="byline"><span class="byline__src">%s</span>'
                '<span class="byline__dot">&bull;</span><time datetime="%s">%s</time></p>'
                '</div></article>'
                % (g.esc(v["video_id"]), g.esc(v["title"]), g.esc(v.get("link", "")),
                   g.esc(v["title"]), g.esc(v.get("channel", "")),
                   g.esc(v.get("published", "")),
                   g.esc(g.human_age(g.parse_dt(v.get("published")) or g.now_utc()))))
        html.append('<div class="vgrid">%s</div>' % "".join(cards))
        html.append('<p class="prose" style="font-size:13px;color:var(--paper-3)">'
                    'Videos play from the original creator&rsquo;s own YouTube player. '
                    'Gospel News Access does not re-host, download or watermark '
                    'anyone&rsquo;s footage.</p>')
    else:
        html.append(L.empty(
            "No channels are connected yet",
            "<p>This page is built and working — it simply has no channels to show "
            "yet. The video wall reads <code>data/video-sources.json</code>, which "
            "is currently an empty list on purpose.</p>"
            "<p><strong>To switch it on:</strong> add a YouTube channel ID to that "
            "file. The video script runs every six hours and the wall fills itself "
            "in. Nothing else needs to change.</p>"
            "<p>Videos always play from the original creator&rsquo;s own player. "
            "Gospel News Access does not re-host or watermark anyone&rsquo;s "
            "footage.</p>"))
    html.append("</main>")
    html.append(L.footer(0))
    g.write_text("video.html", "".join(html))


# ---------------------------------------------------------------------------
# A small helper for the pages that are mostly words
# ---------------------------------------------------------------------------
def prose_page(path: str, nav_key: str, title: str, description: str,
               body: str, depth: int = 0, crumbs=None, extra_schema=None) -> None:
    url = SITE + "/" + path
    schema = []
    if crumbs:
        schema.append(L.breadcrumbs(crumbs))
    if extra_schema:
        schema.extend(extra_schema)
    html = [
        L.head(title, description, url, depth, schema),
        L.breaking_banner(stories(), depth),
        L.header(depth),
        L.nav(nav_key, depth),
        '<main id="main" class="wrap"><div class="prose">',
        body,
        "</div></main>",
        L.footer(depth),
    ]
    g.write_text(path, "".join(html))


def disabled_form(intro_html: str, fields_html: str, endpoint, submit_label: str) -> str:
    """
    Render a form. If no endpoint is configured the form shows its fields but
    CANNOT be submitted, and says so plainly.

    Why: this is a static website. There is no server behind it to catch a
    submission. A form that quietly posts nowhere is worse than no form at
    all — somebody believes they have sent you their music, or asked for help,
    and nothing arrived. So it is visibly switched off until it is real.
    """
    if endpoint:
        return ('<form class="form" method="POST" action="%s">%s%s'
                '<button class="btn" type="submit">%s</button></form>'
                % (g.esc(endpoint), intro_html, fields_html, g.esc(submit_label)))
    return (
        '<div class="note note--warn"><p><strong>This form is not switched on yet.</strong> '
        'The fields below show exactly what will be asked for. Submission is '
        'disabled on purpose until the destination inbox is connected, so that '
        'nothing you type disappears into nowhere.</p></div>'
        '<form class="form" onsubmit="return false">%s<fieldset disabled style="border:0;padding:0;margin:0">%s'
        '<button class="btn btn--disabled" type="button" disabled>%s &mdash; not yet active</button>'
        '</fieldset></form>' % (intro_html, fields_html, g.esc(submit_label))
    )


def field(name, label, kind="text", required=False, hint="", options=None, rows=0) -> str:
    req = ' <span class="req">*</span>' if required else ""
    r = " required" if required else ""
    hint_html = '<p class="hint">%s</p>' % hint if hint else ""
    if options:
        opts = "".join('<option>%s</option>' % g.esc(o) for o in options)
        ctl = '<select id="%s" name="%s"%s><option value="">Choose…</option>%s</select>' % (name, name, r, opts)
    elif rows:
        ctl = '<textarea id="%s" name="%s" rows="%d"%s></textarea>' % (name, name, rows, r)
    else:
        ctl = '<input id="%s" name="%s" type="%s"%s>' % (name, name, kind, r)
    return ('<div class="field"><label for="%s">%s%s</label>%s%s</div>'
            % (name, g.esc(label), req, ctl, hint_html))


# ---------------------------------------------------------------------------
# PAGE: charts
# ---------------------------------------------------------------------------
CHART_META = [
    ("gospel_20", "GNA Gospel 20", 20,
     "The twenty biggest gospel records in the country this week."),
    ("christian_20", "GNA Christian 20", 20,
     "The twenty biggest Christian and worship records this week."),
    ("albums_20", "GNA Albums 20", 20,
     "The twenty biggest gospel and Christian albums this week."),
    ("whats_hot", "What's Hot", 10,
     "Ten slots, fastest movers only. Nothing sits here on reputation."),
]


def _chart_table(entries: list[dict]) -> str:
    rows = []
    for e in entries:
        pos, last = e.get("current_position"), e.get("last_week")
        if e.get("debut"):
            mv = '<span class="mv mv--new">NEW</span>'
        elif e.get("re_entry"):
            mv = '<span class="mv mv--re">RE</span>'
        elif last is None:
            mv = '<span class="mv mv--same">&ndash;</span>'
        elif last > pos:
            mv = '<span class="mv mv--up">&#9650;%d</span>' % (last - pos)
        elif last < pos:
            mv = '<span class="mv mv--down">&#9660;%d</span>' % (pos - last)
        else:
            mv = '<span class="mv mv--same">&ndash;</span>'
        bullet = ' <span title="upward mover" style="color:var(--gold)">&#9679;</span>' if e.get("bullet") else ""
        rows.append(
            '<tr><td class="pos">%d</td><td>%s</td>'
            '<td><span class="ttl">%s</span>%s<br><span class="art">%s</span></td>'
            '<td class="num">%s</td><td class="num">%d</td><td class="num">%d</td>'
            '<td class="art">%s</td></tr>'
            % (pos, mv, g.esc(e.get("title", "")), bullet, g.esc(e.get("artist", "")),
               last if last else "&ndash;", e.get("peak_position", pos),
               e.get("weeks_on_chart", 1), g.esc(e.get("label_or_independent", "")))
        )
    return (
        '<div class="tablewrap"><table class="charttable">'
        '<thead><tr><th style="text-align:right">#</th><th>Move</th><th>Title / Artist</th>'
        '<th style="text-align:right">Last</th><th style="text-align:right">Peak</th>'
        '<th style="text-align:right">Wks</th><th>Label</th></tr></thead>'
        '<tbody>%s</tbody></table></div>' % "".join(rows)
    )


def render_charts() -> None:
    hist = g.read_json("data/charts/history.json", {}) or {}
    charts = hist.get("charts", {})
    published = hist.get("last_published")
    body = ['<h1>The GNA Charts</h1>']

    if published:
        body.append('<p class="dateline">Chart week of %s &middot; published Tuesdays '
                    'at 12:00 noon Pacific</p>' % g.esc(published))
    body.append(
        '<p class="lede">Four weekly charts, measured by Gospel News Access. '
        'These are our own charts &mdash; our own measuring instrument. They are '
        'not derived from, licensed from, or dependent on any other '
        'publication&rsquo;s chart.</p>'
        '<p><a href="charts/methodology.html">How these charts are built</a> '
        '&middot; <a href="charts/panel.html">Who reports to us</a> '
        '&middot; <a href="submit-music.html">Submit your music</a></p>')

    if not charts:
        body.append(L.empty(
            "No chart has published yet",
            "<p>The chart engine is built, tested and scheduled &mdash; it runs "
            "every Tuesday at 12:00 noon Pacific. It has not yet published a "
            "chart because it has not yet received a full tracking week of "
            "data.</p>"
            "<p>We will not publish an invented chart to fill this space. A chart "
            "with no measurement behind it is not a chart. What appears here will "
            "be the real result of real reported spins, real streaming movement "
            "and real release activity.</p>"
            "<p>Two things start the clock: radio and streaming programmers "
            "joining the <a href=\"charts/panel.html\">reporter panel</a>, and "
            "artists and labels <a href=\"submit-music.html\">submitting "
            "music</a>.</p>"))
    else:
        for key, name, size, blurb in CHART_META:
            entries = (charts.get(key) or {}).get("entries", [])
            body.append('<h2 id="%s">%s</h2>' % (key.replace("_", "-"), g.esc(name)))
            body.append("<p>%s</p>" % g.esc(blurb))
            if entries:
                body.append(_chart_table(entries))
            else:
                body.append(L.empty("This chart has no entries this week",
                                    "<p>Not enough measured activity to fill it. "
                                    "It is left empty rather than padded.</p>"))
        recurrents = hist.get("recurrents", [])
        if recurrents:
            body.append("<h2>Recurrents</h2>")
            body.append("<p>Titles that have spent more than 20 weeks on a chart and "
                        "remain popular move here, so long-running records do not "
                        "block new music from charting.</p>")
            body.append(_chart_table(recurrents))

    body.append(
        '<div class="declaration">Gospel News Access does not accept payment for '
        'chart consideration, chart position, or reporter panel membership. Any '
        'offer to buy placement will be declined and may be reported.</div>')

    prose_page("charts.html", "charts", "The GNA Charts",
               "The four Gospel News Access charts — GNA Gospel 20, GNA Christian 20, "
               "GNA Albums 20 and What's Hot. Published every Tuesday at noon Pacific.",
               "".join(body), 0,
               [("Front Page", SITE + "/"), ("Charts", SITE + "/charts.html")])


def render_methodology() -> None:
    c = cfg().get("charts", {})
    panel = c.get("editorial_panel") or []
    if panel:
        panel_html = "<ul>%s</ul>" % "".join("<li>%s</li>" % g.esc(p) for p in panel)
    else:
        panel_html = ('<p>The editorial desk is not yet seated. Until it is, the '
                      'editorial input is zero and the charts are produced entirely '
                      'by the three measured inputs above. This is stated here '
                      'rather than left vague, because a reader is entitled to know '
                      'exactly who can and cannot influence a position.</p>')

    body = f"""<h1>How the GNA Charts Are Built</h1>
<p class="lede">This page exists so that anyone &mdash; an artist, a label, a radio
programmer, a reader &mdash; can see exactly how a position on a Gospel News Access
chart is arrived at. Nothing here is hidden.</p>

<div class="declaration">Gospel News Access does not accept payment for chart
consideration, chart position, or reporter panel membership. Any offer to buy
placement will be declined and may be reported.</div>

<h2>What these charts are</h2>
<p>Four weekly charts: the <strong>GNA Gospel 20</strong>, the <strong>GNA
Christian 20</strong>, the <strong>GNA Albums 20</strong>, and <strong>What&rsquo;s
Hot</strong> (ten slots, fastest movers only).</p>
<p>They are Gospel News Access&rsquo;s own charts &mdash; our own measuring
instrument. They are <strong>not</strong> derived from, licensed from, or dependent
on any other publication&rsquo;s chart.</p>

<h2>What is measured, and how much each part counts</h2>
<table class="dtable">
<thead><tr><th>Input</th><th>Weight</th><th>What it actually is</th></tr></thead>
<tbody>
<tr><td><strong>Reporter panel</strong></td><td>40%</td>
<td>Gospel radio stations, syndicated shows, streaming programmers and DJs who
voluntarily report their weekly spin counts to us. Every reporter is named
publicly on the <a href="panel.html">reporter panel page</a>.</td></tr>
<tr><td><strong>Streaming and video momentum</strong></td><td>35%</td>
<td>Week-over-week <strong>change</strong>, never cumulative totals. This matters:
if you count total plays, a 20-year-old classic sits at number one forever and
no new record can ever chart. We measure movement, not accumulation.</td></tr>
<tr><td><strong>Release and submission activity</strong></td><td>15%</td>
<td>New releases, radio singles worked to programmers, and material submitted
through <a href="../submit-music.html">the submission form</a>.</td></tr>
<tr><td><strong>Editorial desk</strong></td><td>10%</td>
<td>Human judgement, applied last. Every single adjustment is written down with
a one-line reason in a public log.</td></tr>
</tbody></table>

<h2>The editorial desk cannot rescue a record</h2>
<p>The editorial input is capped at 10%, and the chart is built so that it
computes and publishes correctly <strong>with the editorial input at zero</strong>.
The three measured inputs alone produce a valid chart. If nobody touches it in a
given week, it still goes out on time.</p>
{panel_html}

<h2>The tracking week</h2>
<p>Friday 12:00 AM Pacific through Thursday 11:59 PM Pacific.</p>
<p>Submission cutoff is <strong>Thursday 11:59 PM Pacific</strong>. Anything
arriving after that is considered in the following week &mdash; it is not lost.</p>
<p>Charts publish every <strong>Tuesday at 12:00 noon Pacific</strong>, without
exception.</p>

<h2>How reporter spins are normalised</h2>
<p>A station reaching two million people and a station reaching eight thousand
cannot both count as &ldquo;one spin&rdquo;. Reported spins are weighted by station
tier:</p>
<table class="dtable">
<thead><tr><th>Tier</th><th>What it means</th><th>Weight</th></tr></thead>
<tbody>
<tr><td>Tier A</td><td>Major-market terrestrial radio and nationally syndicated shows</td><td>&times;1.00</td></tr>
<tr><td>Tier B</td><td>Regional and secondary-market terrestrial stations</td><td>&times;0.65</td></tr>
<tr><td>Tier C</td><td>Local, community, internet-only radio and individual programmers/DJs</td><td>&times;0.35</td></tr>
</tbody></table>
<p>A reporter&rsquo;s tier is recorded on the <a href="panel.html">panel page</a>
alongside their name. Tier is assigned on measurable reach, never on
relationship, and never on payment.</p>

<h2>How long a record stays</h2>
<ul>
<li>A title falls off after <strong>20 weeks</strong> on a chart, unless it is
still in the top 10.</li>
<li>Long-running titles move to a <strong>Recurrents</strong> list, so that a
record everybody already knows does not block a new one from charting.</li>
<li>A title returning after falling off is flagged <strong>RE</strong> and
<strong>resumes its previous peak</strong> &mdash; its history is not erased.</li>
<li>A first appearance is flagged <strong>NEW</strong>.</li>
<li>A title moving upward carries a <strong>bullet</strong>.</li>
</ul>
<p><strong>Weeks on chart</strong> and <strong>peak position</strong> are real
running totals kept in a file that persists from week to week. They are never
recalculated from scratch. A chart that recomputes its own history each week is
producing fiction, and we will not do that.</p>

<h2>Streaming sources, and a note on permission</h2>
<p>Before any platform is used as a chart input, we read that platform&rsquo;s own
developer terms on ranking and chart creation. If the terms do not permit it, the
source is dropped and its share of the weight is redistributed across the
remaining measured inputs. We do not use a source quietly and hope.</p>
<p>The current status of every candidate source &mdash; including which ones are
switched off and why &mdash; is recorded in
<code>data/chart-sources.json</code> in our public repository.</p>

<h2>If you think a position is wrong</h2>
<p>Tell us and we will check it. Send the chart name, the chart week, the title
and artist, and what you believe the correct figure is. Data errors are corrected
openly and the correction is noted on our
<a href="../corrections.html">corrections page</a>.</p>
{_contact_line('email_charts', 'Chart data questions')}

<h2>What will get you removed</h2>
<p>Falsified spin reports, or any attempt to buy a position, end a
reporter&rsquo;s participation permanently and the removal is stated publicly on
the panel page.</p>
"""
    prose_page("charts/methodology.html", "charts", "Chart Methodology",
               "Exactly how a position on a Gospel News Access chart is calculated: "
               "the four weighted inputs, the tracking week, and the rules.",
               body, 1,
               [("Front Page", SITE + "/"), ("Charts", SITE + "/charts.html"),
                ("Methodology", SITE + "/charts/methodology.html")])


def _contact_line(key: str, label: str) -> str:
    """Render a contact line only if a real address exists. Otherwise nothing."""
    addr = (cfg().get("organization") or {}).get(key)
    if not addr:
        return ('<div class="note"><p>A dedicated inbox for this is being set up. '
                'Until it is live we are not printing an address here, because an '
                'address that nobody reads is worse than none.</p></div>')
    return '<p><strong>%s:</strong> <a href="mailto:%s">%s</a></p>' % (
        g.esc(label), g.esc(addr), g.esc(addr))


def render_panel() -> None:
    reporters = g.read_json("data/reporters.json", {"reporters": []}) or {"reporters": []}
    rows = reporters.get("reporters", [])
    body = ["<h1>The GNA Reporter Panel</h1>",
            '<p class="lede">These are the radio stations, syndicated shows, '
            'streaming programmers and DJs who voluntarily report their weekly '
            'spin counts to Gospel News Access. Their reporting is 40% of every '
            'chart position.</p>',
            '<p>We name every reporter publicly. A chart whose panel is secret '
            'cannot be checked by anybody, and a chart nobody can check is just an '
            'opinion with numbers on it.</p>']

    if rows:
        trs = "".join(
            '<tr><td><strong>%s</strong></td><td>%s</td><td>%s</td><td>%s</td></tr>'
            % (g.esc(r.get("name", "")), g.esc(r.get("market", "")),
               g.esc(r.get("tier", "")), g.esc(r.get("reporting_since", "")))
            for r in rows)
        body.append('<table class="dtable"><thead><tr><th>Reporter</th><th>Market</th>'
                    '<th>Tier</th><th>Reporting since</th></tr></thead>'
                    '<tbody>%s</tbody></table>' % trs)
    else:
        body.append(L.empty(
            "The panel is being built now",
            "<p>No reporters have joined yet, so none are listed. We are not "
            "listing stations that have not agreed to report &mdash; naming a "
            "station that never signed up would be a lie about our own chart.</p>"
            "<p>This page fills in as real reporters join.</p>"))

    body.append("""<h2>Who can join</h2>
<p>Gospel and Christian radio stations, syndicated programmes, streaming
programmers, and working DJs who can report an honest weekly spin count.</p>

<h2>What reporting involves</h2>
<ul>
<li>One weekly report of what you actually played and how many times.</li>
<li>Submitted by Thursday 11:59 PM Pacific, covering Friday through Thursday.</li>
<li>Your station is named publicly on this page, with its market and tier.</li>
</ul>

<h2>What it costs</h2>
<div class="declaration">Gospel News Access does not accept payment for chart
consideration, chart position, or reporter panel membership. Any offer to buy
placement will be declined and may be reported.</div>
<p>Panel membership is free and always will be. Nobody buys their way onto this
page, and no reporter receives anything of value for reporting.</p>

<h2>How tiers are set</h2>
<p>Tier is assigned on measurable reach alone &mdash; never on relationship, never
on payment. The weighting is published in full on the
<a href="methodology.html">methodology page</a>.</p>

<h2>Falsified reports</h2>
<p>A falsified spin report ends participation permanently, and the removal is
stated publicly on this page. The charts are only worth something if the numbers
behind them are real.</p>
""")
    body.append(_contact_line("email_charts", "Reporter panel enquiries"))
    prose_page("charts/panel.html", "charts", "Reporter Panel",
               "The named radio stations, shows and programmers who report weekly "
               "spin counts to the Gospel News Access charts.",
               "".join(body), 1,
               [("Front Page", SITE + "/"), ("Charts", SITE + "/charts.html"),
                ("Reporter Panel", SITE + "/charts/panel.html")])


# ---------------------------------------------------------------------------
# PAGE: submit music
# ---------------------------------------------------------------------------
def render_submit_music() -> None:
    endpoint = (cfg().get("forms") or {}).get("music_submission_endpoint")
    fields = "".join([
        field("artist", "Artist name", required=True),
        field("track_title", "Track title", required=True),
        field("release_date", "Release date", "date", required=True),
        field("label_or_independent", "Label or independent", required=True,
              hint="Write the label name, or the word Independent."),
        field("isrc", "ISRC", hint="If you have one. Leave blank if not — it is not required."),
        field("streaming_links", "Streaming links", rows=3, required=True,
              hint="Spotify, Apple Music, YouTube, Audiomack — whatever is live."),
        field("radio_single", "Is this being worked to radio as a single?",
              required=True, options=["Yes", "No"]),
        field("contact_email", "Contact email", "email", required=True,
              hint="Where we reply. This is not published."),
        field("press_photo", "Press photo URL", required=True,
              hint="A link to a high-resolution photo we are permitted to use."),
        field("bio", "One-paragraph biography", rows=5, required=True),
    ])
    intro = ""
    tracking = _tracking_week_text()
    body = f"""<h1>Submit Music to the GNA Charts</h1>
<p class="lede">Any gospel or Christian artist, label, publicist or manager may
submit. Submission is free.</p>

<div class="declaration">Gospel News Access does not accept payment for chart
consideration, chart position, or reporter panel membership. Any offer to buy
placement will be declined and may be reported.</div>

<h2>Before you submit, two honest things</h2>
<ul>
<li><strong>Submitting does not guarantee charting.</strong> Submission counts
toward the release and submission input, which is 15% of a chart position. The
other 85% is reported radio spins and measured streaming movement. Nobody can
submit their way onto a chart.</li>
<li><strong>The current tracking week is {g.esc(tracking)}.</strong> Submissions
received after Thursday 11:59 PM Pacific are considered in the following week.
Nothing is thrown away.</li>
</ul>

{disabled_form(intro, fields, endpoint, "Submit music")}

<h2>What happens after you submit</h2>
<ol>
<li>You receive an automatic reply confirming which tracking week your
submission falls into, and restating that submission does not guarantee
charting.</li>
<li>Your record is added to the release and submission pool for that week.</li>
<li>If it charts, it appears on the following Tuesday at 12:00 noon Pacific.</li>
</ol>
<p>Submissions are stored in <code>data/submissions/</code>. Your contact email
and any private material are never published.</p>
<p>How positions are calculated is set out in full on the
<a href="charts/methodology.html">chart methodology page</a>.</p>
"""
    prose_page("submit-music.html", "submit", "Submit Music",
               "Submit gospel or Christian music for consideration on the GNA charts. "
               "Free to submit; submission does not guarantee charting.",
               body, 0,
               [("Front Page", SITE + "/"), ("Submit Music", SITE + "/submit-music.html")])


def _tracking_week_text() -> str:
    """The current Friday 12:00 AM – Thursday 11:59 PM Pacific window."""
    now = g.now_pacific()
    days_since_friday = (now.weekday() - 4) % 7  # Monday=0 ... Friday=4
    start = (now - timedelta(days=days_since_friday)).replace(
        hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=6)
    return "%s through %s Pacific" % (start.strftime("%A, %B %-d"), end.strftime("%A, %B %-d"))


# ---------------------------------------------------------------------------
# PAGES: the CDC
#
# SAFETY: people in crisis may act on what these pages say. A programme listed
# that does not exist, or a number that rings nowhere, does real harm to
# somebody already in trouble. So every fact is read from site-config.json and
# a missing fact renders as NOTHING — never a placeholder, never a guess.
# ---------------------------------------------------------------------------
def _cdc_facts(block: dict) -> str:
    """Render only the contact facts that genuinely exist."""
    out = []
    if block.get("address"):
        out.append("<p><strong>Address:</strong> %s</p>" % g.esc(block["address"]))
    if block.get("phone"):
        out.append('<p><strong>Phone:</strong> <a href="tel:%s">%s</a></p>'
                   % (g.esc(block["phone"]), g.esc(block["phone"])))
    if block.get("email"):
        out.append('<p><strong>Email:</strong> <a href="mailto:%s">%s</a></p>'
                   % (g.esc(block["email"]), g.esc(block["email"])))
    if block.get("hours"):
        out.append("<p><strong>Hours:</strong> %s</p>" % g.esc(block["hours"]))
    if not out:
        return ('<div class="note note--warn"><p><strong>We are not printing an '
                'address or phone number here yet.</strong> Publishing one that has '
                'not been confirmed would send somebody who needs help to a door '
                'that does not open or a number that does not ring. The details go '
                'up the moment they are confirmed.</p></div>')
    return "".join(out)


def _cdc_programs(block: dict, who: str) -> str:
    programs = block.get("programs") or []
    if not programs:
        return ('<div class="note note--warn"><p><strong>The programme list is '
                'being confirmed and is deliberately blank.</strong></p>'
                '<p>We will not list a service that %s cannot actually deliver '
                'today. If you are in need right now, please contact us directly '
                'rather than relying on this page &mdash; and if your need is urgent, '
                'contact your local emergency services or a established local '
                'agency, who can help immediately.</p></div>' % g.esc(who))
    out = []
    for p in programs:
        out.append("<h3>%s</h3><p>%s</p>" % (g.esc(p.get("name", "")), g.esc(p.get("description", ""))))
        if p.get("eligibility"):
            out.append("<p><strong>Who it is for:</strong> %s</p>" % g.esc(p["eligibility"]))
        if p.get("contact"):
            out.append("<p><strong>How to reach it:</strong> %s</p>" % g.esc(p["contact"]))
    return "".join(out)


def _donate_block() -> str:
    if (cfg().get("cdc") or {}).get("donations_enabled"):
        return ""  # a real processor would be wired in here
    return ('<h2>Giving</h2><div class="note note--warn">'
            '<p><strong>Online giving is not switched on yet.</strong> The button '
            'below is deliberately disabled. We will not take a card payment '
            'through a link that has no real payment processor behind it.</p>'
            '<p><button class="btn btn--disabled" type="button" disabled>'
            'Donate &mdash; not yet active</button></p></div>')


def render_cdc() -> None:
    conf = cfg().get("cdc") or {}
    crumbs = [("Front Page", SITE + "/"), ("CDC", SITE + "/cdc/index.html")]

    body = """<h1>Community Development</h1>
<p class="lede">Gospel News Access supports two community development centres.
This section is how to find them and what they actually do.</p>
<div class="note"><p>Everything on these pages is either confirmed or it is not
here. We do not list a programme, a partner, a phone number or an address that
has not been verified &mdash; because somebody in real need may act on what they
read on this page.</p></div>
<h2>The two centres</h2>
<h3><a href="gospel-news-access.html">Gospel News Access CDC</a></h3>
<p>The community development arm of Gospel News Access.</p>
<h3><a href="his-presence-fire.html">His Presence Fire Ministries CDC</a></h3>
<p>The community development arm of His Presence Fire Ministries.</p>
"""
    prose_page("cdc/index.html", "cdc", "Community Development",
               "The two community development centres supported by Gospel News Access.",
               body, 1, crumbs)

    # --- Gospel News Access CDC ---
    b = conf.get("gospel_news_access") or {}
    body = f"""<h1>Gospel News Access CDC</h1>
<p class="lede">The community development arm of Gospel News Access.</p>
<h2>Contact</h2>
{_cdc_facts(b)}
<h2>Programmes and services</h2>
{_cdc_programs(b, 'this centre')}
{_partners_block(b)}
{_donate_block()}
<h2>Get in touch</h2>
{disabled_form('', ''.join([
    field('name', 'Your name', required=True),
    field('email', 'Email', 'email', required=True),
    field('phone', 'Phone', 'tel'),
    field('message', 'How can we help?', rows=5, required=True),
]), (cfg().get('forms') or {}).get('cdc_contact_endpoint'), 'Send')}
"""
    prose_page("cdc/gospel-news-access.html", "cdc", "Gospel News Access CDC",
               "The community development arm of Gospel News Access.",
               body, 1, crumbs + [("Gospel News Access CDC", SITE + "/cdc/gospel-news-access.html")])

    # --- His Presence Fire Ministries CDC ---
    b = conf.get("his_presence_fire") or {}
    services = ""
    if b.get("service_times_public"):
        services = "<h2>Service times</h2><p>%s</p>" % g.esc(b["service_times_public"])
    # THE ZOOM RULE: a meeting ID, dial-in number or password is NEVER printed
    # here or anywhere else on this site. The link is sent on request.
    zoom = ('<h2>Thursday service online</h2>'
            '<div class="note"><p>%s</p><p>Ask us for the link using the form below '
            'and we will send it to you directly.</p></div>'
            % g.esc(b.get("zoom_note") or
                    "Thursday service is held online. The link is sent on request — "
                    "it is never published on this site."))
    body = f"""<h1>His Presence Fire Ministries CDC</h1>
<p class="lede">The community development arm of His Presence Fire Ministries.</p>
<h2>Contact</h2>
{_cdc_facts(b)}
{services}
{zoom}
<h2>Programmes and services</h2>
{_cdc_programs(b, 'this ministry')}
{_partners_block(b)}
{_donate_block()}
<h2>Request the service link, or get in touch</h2>
{disabled_form('', ''.join([
    field('name', 'Your name', required=True),
    field('email', 'Email', 'email', required=True),
    field('reason', 'What are you contacting us about?', required=True,
          options=['Request the Thursday service link', 'Programmes and services',
                   'Volunteering', 'Something else']),
    field('message', 'Message', rows=5),
]), (cfg().get('forms') or {}).get('cdc_contact_endpoint'), 'Send')}
"""
    prose_page("cdc/his-presence-fire.html", "cdc", "His Presence Fire Ministries CDC",
               "The community development arm of His Presence Fire Ministries.",
               body, 1, crumbs + [("His Presence Fire CDC", SITE + "/cdc/his-presence-fire.html")])


def _partners_block(b: dict) -> str:
    partners = b.get("partners") or []
    if not partners:
        return ""   # renders as nothing — never a fake partner logo wall
    return ("<h2>Partners</h2><ul>%s</ul>"
            % "".join("<li>%s</li>" % g.esc(p) for p in partners))


# ---------------------------------------------------------------------------
# PAGE: church directory
#
# THE SOURCING RULE, enforced here in code:
#   An entry marked "Unverified" renders with NO contact detail at all —
#   no website, no service times, no social. Only the name and location.
#   A wrong detail sends somebody to the wrong church on a Sunday morning.
# ---------------------------------------------------------------------------
CONF_LABEL = {
    "confirmed": ("Confirmed current", "pill--confirmed"),
    "likely": ("Likely current", "pill--likely"),
    "unverified": ("Unverified", "pill--unverified"),
}


def render_churches() -> None:
    doc = g.read_json("data/churches-public.json", {"churches": []}) or {"churches": []}
    rows = doc.get("churches", [])
    body = ["<h1>Church Directory</h1>",
            '<p class="lede">A public directory of gospel and Christian churches. '
            'Everything listed here comes from the church&rsquo;s own public page or '
            'from a church that asked to be listed.</p>',
            '<p><a href="churches/join.html">Add your church &rarr;</a></p>']

    if rows:
        trs = []
        for ch in rows:
            conf = (ch.get("confidence") or "unverified").lower()
            label, cls = CONF_LABEL.get(conf, CONF_LABEL["unverified"])
            loc = ", ".join(x for x in [ch.get("city"), ch.get("state"), ch.get("country")] if x)

            # An unverified entry shows NO contact detail. This is the rule.
            if conf == "unverified":
                detail = ('<span style="color:var(--paper-3)">Contact details are '
                          'withheld until this entry is verified.</span>')
            else:
                bits = []
                if ch.get("website"):
                    bits.append('<a href="%s" rel="noopener nofollow" target="_blank">Website</a>'
                                % g.esc(ch["website"]))
                if ch.get("service_times"):
                    bits.append(g.esc(ch["service_times"]))
                for handle in (ch.get("social") or []):
                    bits.append('<a href="%s" rel="noopener nofollow" target="_blank">%s</a>'
                                % (g.esc(handle.get("url", "")), g.esc(handle.get("platform", "Social"))))
                detail = " &middot; ".join(bits) or "&mdash;"

            verified_note = ""
            if ch.get("verified_date"):
                verified_note = ('<br><span style="font-size:11px;color:var(--paper-3)">'
                                 'Verified %s%s</span>'
                                 % (g.esc(ch["verified_date"]),
                                    " &middot; " + g.esc(ch["verified_method"]) if ch.get("verified_method") else ""))
            trs.append(
                '<tr><td><strong>%s</strong>%s</td><td>%s</td><td>%s</td>'
                '<td><span class="pill %s">%s</span>%s</td><td>%s</td></tr>'
                % (g.esc(ch.get("name", "")),
                   "<br><span class='art'>%s</span>" % g.esc(ch["senior_pastor"]) if ch.get("senior_pastor") else "",
                   g.esc(loc), g.esc(ch.get("denomination", "")),
                   cls, g.esc(label), verified_note, detail))
        body.append('<div class="tablewrap"><table class="dtable"><thead><tr>'
                    '<th>Church / Senior Pastor</th><th>Location</th><th>Denomination</th>'
                    '<th>Confidence</th><th>Public details</th></tr></thead>'
                    '<tbody>%s</tbody></table></div>' % "".join(trs))
    else:
        body.append(L.empty(
            "The directory is open and has no entries yet",
            "<p>This directory is built and ready. It has no churches in it yet "
            "because we have not yet added one that meets the sourcing rule below "
            "&mdash; and we would rather show you nothing than show you a list we "
            "assembled by guesswork.</p>"
            "<p><a href=\"churches/join.html\">Add your church &rarr;</a></p>"))

    body.append("""<h2>How an entry gets here</h2>
<p>Two ways only:</p>
<ol>
<li>The church asked to be listed, through the form.</li>
<li>We took it from the church&rsquo;s own public page.</li>
</ol>
<p>We never publish a personal mobile number, a home address, or an email address
that we worked out from a pattern. A guessed address that bounces burns that
address permanently, and it is rude.</p>

<h2>What the confidence labels mean</h2>
<table class="dtable">
<thead><tr><th>Label</th><th>Meaning</th></tr></thead>
<tbody>
<tr><td><span class="pill pill--confirmed">Confirmed current</span></td>
<td>Checked within the last 90 days. The date and the method are shown on the entry.</td></tr>
<tr><td><span class="pill pill--likely">Likely current</span></td>
<td>From a public source we trust, but not re-checked within 90 days.</td></tr>
<tr><td><span class="pill pill--unverified">Unverified</span></td>
<td><strong>No contact details are shown at all</strong> &mdash; only the name and
location. We will not send you to a door we have not checked.</td></tr>
</tbody></table>

<h2>Corrections and removal</h2>
<p>If something here about your church is wrong, or you want the entry taken
down, tell us and we will fix or remove it. We do not require a reason.</p>
""")
    body.append(_contact_line("email_general", "Directory corrections"))
    prose_page("churches.html", "churches", "Church Directory",
               "A public directory of gospel and Christian churches, sourced from "
               "churches' own public pages and opt-in listings.",
               "".join(body), 0,
               [("Front Page", SITE + "/"), ("Churches", SITE + "/churches.html")])

    # --- the opt-in form ---
    endpoint = (cfg().get("forms") or {}).get("church_join_endpoint")
    fields = "".join([
        field("church_name", "Church name", required=True),
        field("senior_pastor", "Senior pastor's name", required=True,
              hint="Exactly as your church publishes it."),
        field("city", "City", required=True),
        field("state", "State / Province", required=True),
        field("country", "Country", required=True),
        field("denomination", "Denomination"),
        field("website", "Church website", "url"),
        field("service_times", "Public service times", rows=2),
        field("social", "Public social media links", rows=2),
        field("submitter_email", "Your email", "email", required=True,
              hint="So we can confirm the listing. This is never published."),
        field("consent", "Do you consent to this being listed publicly?",
              required=True, options=["Yes, list our church publicly"]),
    ])
    body = f"""<h1>Add Your Church</h1>
<p class="lede">Adding your church to the Gospel News Access directory is free.</p>
<h2>What we publish</h2>
<p>Only what you enter below, and only what a church would normally put on its own
website: the church name, city, state, country, denomination, public website,
public service times, public social handles, and your senior pastor&rsquo;s name
as your church itself publishes it.</p>
<h2>What we never publish</h2>
<ul>
<li>A personal mobile number.</li>
<li>A home address.</li>
<li>Your email address &mdash; we use it to confirm the listing, and that is all.</li>
</ul>
<p>You can ask us to change or remove your listing at any time, and we will, without
asking why.</p>
{disabled_form('', fields, endpoint, "Submit church listing")}
<p>Read the full sourcing and confidence rules on the
<a href="../churches.html">directory page</a>.</p>
"""
    prose_page("churches/join.html", "churches", "Add Your Church",
               "Add your church to the Gospel News Access public directory. Free, "
               "opt-in, and removable at any time.",
               body, 1,
               [("Front Page", SITE + "/"), ("Churches", SITE + "/churches.html"),
                ("Add Your Church", SITE + "/churches/join.html")])


# ---------------------------------------------------------------------------
# PAGES: about / masthead / contact / corrections / privacy  (E-E-A-T)
# ---------------------------------------------------------------------------
def render_eeat() -> None:
    c = cfg().get("organization") or {}

    # --- About ---
    own = c.get("ownership_disclosure")
    if own:
        own_html = "<p>%s</p>" % g.esc(own)
    else:
        own_html = ('<p>Gospel News Access is owned by %s. A fuller ownership and '
                    'funding statement is being prepared and will be published here. '
                    'We would rather leave this short and accurate than pad it with '
                    'claims we have not checked.</p>' % g.esc(c.get("owner_name", "its founder")))
    founded = ("<p>Gospel News Access has been publishing since %s.</p>"
               % g.esc(str(c["founded_year"]))) if c.get("founded_year") else ""

    body = f"""<h1>About Gospel News Access</h1>
<p class="lede">Gospel News Access is an independent gospel, Christian and faith
news wire. We aggregate the faith world&rsquo;s reporting, we produce our own
original reporting, and we publish our own music charts.</p>
{founded}

<h2>Who owns this publication</h2>
{own_html}
<p><strong>{g.esc(c.get('owner_name',''))}</strong> &mdash; {g.esc(c.get('owner_role',''))}</p>
<p>{g.esc(c.get('owner_bio',''))}</p>

<h2>How the wire works</h2>
<p>Most of what you see on the front page is a <strong>news wire</strong>: headlines
from other publications, gathered automatically every 30 minutes. When you click
one, you go to the publication that reported it. The photograph shown is the
publisher&rsquo;s own image, credited to them, displayed from their servers. We do
not copy it, re-host it, crop out a credit or put our name on it. This is the same
model Google News and Flipboard use.</p>
<p>Our <strong>own reporting</strong> is always clearly bylined as Gospel News
Access and lives on our own pages.</p>

<h2>Our editorial standards</h2>
<ul>
<li>We do not invent anything &mdash; not a quote, a source, a statistic, a church,
a programme, an event or an outcome. Not once, not to fill a gap.</li>
<li>Every original story carries a real dateline and a real timestamp.</li>
<li>Where there is no named reporter, the byline is
<strong>Gospel News Access Staff</strong>. We do not invent a journalist&rsquo;s
name to put on a story.</li>
<li>A story about a named individual&rsquo;s conduct requires either primary
documentation or an on-record source, <strong>and</strong> a genuine attempt to
reach that person for comment before we publish. If we have neither, the story
does not run.</li>
<li>When we get something wrong we correct it openly, on the story and on our
<a href="corrections.html">corrections page</a>. We do not quietly edit and
pretend it never happened.</li>
</ul>

<h2>Money</h2>
<div class="declaration">Gospel News Access does not accept payment for chart
consideration, chart position, or reporter panel membership. Any offer to buy
placement will be declined and may be reported.</div>
<p>We also do not accept payment for news coverage. If we ever carry advertising
or sponsored material it will be labelled as such, plainly, on the item itself.</p>

<h2>How we are built</h2>
<p>This site is deliberately simple: plain HTML served as static files, updated by
scheduled scripts rather than by a person clicking publish. The code that fetches
the news, extracts the photographs and calculates the charts is open for anyone to
read. Our chart method is published in full on the
<a href="charts/methodology.html">methodology page</a>.</p>

<h2>Contact</h2>
<p>See the <a href="contact.html">contact page</a> and the
<a href="masthead.html">masthead</a>.</p>
"""
    prose_page("about.html", "about", "About & Ownership",
               "Who owns Gospel News Access, how the wire works, and the editorial "
               "standards we hold ourselves to.",
               body, 0, [("Front Page", SITE + "/"), ("About", SITE + "/about.html")],
               [org_schema()])

    # --- Masthead ---
    body = f"""<h1>Masthead</h1>
<p class="lede">Who is responsible for Gospel News Access.</p>
<h2>Ownership</h2>
<p><strong>{g.esc(c.get('owner_name',''))}</strong> &mdash; {g.esc(c.get('owner_role',''))}</p>
<p>{g.esc(c.get('owner_bio',''))}</p>
<h2>Editorial</h2>
<div class="note"><p>Editorial roles beyond the owner are not yet filled, and so
none are listed. We will not print a masthead of invented names or borrowed
titles &mdash; a masthead that cannot be checked is worth nothing.</p>
<p>Wire copy is aggregated automatically and always credited to the publication
that reported it. Original reporting carries the byline
<strong>Gospel News Access Staff</strong> unless a named reporter wrote it.</p></div>
<h2>Corrections</h2>
<p>Our corrections policy lives at a permanent address:
<a href="corrections.html">{g.esc(SITE)}/corrections.html</a></p>
{_contact_line('email_general', 'General enquiries')}
"""
    prose_page("masthead.html", "about", "Masthead",
               "Who is responsible for Gospel News Access.",
               body, 0, [("Front Page", SITE + "/"), ("Masthead", SITE + "/masthead.html")])

    # --- Contact ---
    endpoint = (cfg().get("forms") or {}).get("contact_endpoint")
    fields = "".join([
        field("name", "Your name", required=True),
        field("email", "Email", "email", required=True),
        field("topic", "What is this about?", required=True,
              options=["A news tip", "A correction", "Chart data", "Reporter panel",
                       "Church directory", "Community development", "Something else"]),
        field("message", "Message", rows=6, required=True),
    ])
    addr_html = ""
    if c.get("mailing_address"):
        addr_html = "<h2>Post</h2><p>%s</p>" % g.esc(c["mailing_address"])
    phone_html = ""
    if c.get("phone"):
        phone_html = '<h2>Telephone</h2><p><a href="tel:%s">%s</a></p>' % (
            g.esc(c["phone"]), g.esc(c["phone"]))
    body = f"""<h1>Contact Gospel News Access</h1>
<p class="lede">News tips, corrections, chart questions and directory listings.</p>
{_contact_line('email_general', 'General enquiries')}
{_contact_line('email_corrections', 'Corrections')}
{_contact_line('email_charts', 'Chart data')}
{phone_html}
{addr_html}
<h2>Send us a message</h2>
{disabled_form('', fields, endpoint, "Send message")}
<h2>News tips</h2>
<p>If you are sending a tip about a named individual&rsquo;s conduct, please know
what we will need before we can publish: either primary documentation or a source
willing to go on the record, and we will always approach the person concerned for
comment first. We will not publish an allegation we cannot stand behind.</p>
"""
    prose_page("contact.html", "about", "Contact",
               "How to reach Gospel News Access with a news tip, a correction, or a "
               "chart question.",
               body, 0, [("Front Page", SITE + "/"), ("Contact", SITE + "/contact.html")])

    # --- Corrections (permanent URL) ---
    corr = g.read_json("data/corrections.json", {"corrections": []}) or {"corrections": []}
    rows = corr.get("corrections", [])
    if rows:
        items = "".join(
            '<article style="border-bottom:1px solid var(--line);padding:16px 0">'
            '<p class="dateline">%s</p><h3>%s</h3><p>%s</p>%s</article>'
            % (g.esc(x.get("date", "")), g.esc(x.get("headline", "")), g.esc(x.get("correction", "")),
               '<p><a href="%s">Read the corrected story</a></p>' % g.esc(x["url"]) if x.get("url") else "")
            for x in rows)
        listing = "<h2>Published corrections</h2>" + items
    else:
        listing = ("<h2>Published corrections</h2>" + L.empty(
            "No corrections have been issued",
            "<p>When we issue one it will be listed here permanently, with the date. "
            "This page is not cleared out.</p>"))
    body = f"""<h1>Corrections Policy</h1>
<p class="lede">We get things wrong sometimes. When we do, we say so plainly,
in public, and we leave the record standing.</p>

<h2>What we do when we get something wrong</h2>
<ul>
<li>The correction is added <strong>at the bottom of the story itself</strong>,
with the date it was made, so anyone reading the story sees it.</li>
<li>The correction is also listed <strong>on this page</strong>, permanently, at
this address: <code>{g.esc(SITE)}/corrections.html</code></li>
<li>We do not silently edit a story and pretend the error never happened. If the
substance changes, it is marked.</li>
</ul>

<h2>The difference between a correction and an update</h2>
<p>A <strong>correction</strong> means we published something that was wrong. An
<strong>update</strong> means the situation changed after we published. Both are
marked and dated; they are not the same thing and we do not use one word to hide
the other.</p>

<h2>Wire stories</h2>
<p>Most headlines on our front page are from other publications and link to them.
If one of those stories is wrong, the correction has to come from the publication
that wrote it &mdash; we cannot correct somebody else&rsquo;s reporting. Tell us
anyway: if a story is seriously wrong we will remove it from our wire.</p>

<h2>Chart data</h2>
<p>If you believe a chart position is wrong, send the chart name, the chart week,
the title and artist, and what you believe the correct figure is. Chart data
corrections are listed here like any other.</p>

<h2>How to request a correction</h2>
{_contact_line('email_corrections', 'Corrections')}
<p>Please include the headline, the date, and what specifically is wrong. You do
not have to be the subject of the story to ask.</p>

{listing}
"""
    prose_page("corrections.html", "about", "Corrections Policy",
               "How Gospel News Access corrects mistakes, and every correction we "
               "have issued.",
               body, 0, [("Front Page", SITE + "/"), ("Corrections", SITE + "/corrections.html")])

    # --- Privacy ---
    body = """<h1>Privacy</h1>
<p class="lede">What this website does and does not know about you. In plain
English, because privacy policies that nobody can read protect nobody.</p>

<h2>The short version</h2>
<p>This is a static website. It has no accounts, no logins, and no database of
readers. We do not set advertising cookies and we do not run a tracking pixel.</p>

<h2>Photographs on the wire</h2>
<p>Story photographs are displayed from the original publisher&rsquo;s own servers
rather than copied onto ours. That means when a page loads, the publisher&rsquo;s
server receives the request and can see your IP address, the same as if you had
visited their site. We send no referrer information with those requests.</p>

<h2>Video</h2>
<p>Videos are embedded from YouTube using its no-cookie player, which does not set
tracking cookies until you press play. Once you press play, YouTube&rsquo;s own
privacy policy applies to that playback.</p>

<h2>Links out</h2>
<p>Most headlines here lead to other publications. Once you follow one, you are on
their website under their privacy policy, not ours.</p>

<h2>Forms</h2>
<p>When form submission is switched on, we will use what you send only for the
purpose you sent it: to consider your music, to list your church, or to answer
you. Contact details supplied through a form are never published and never sold.
You may ask us to delete anything you have sent, and we will.</p>

<h2>Hosting</h2>
<p>This site is served by GitHub Pages. GitHub keeps its own server logs; see
GitHub&rsquo;s privacy statement for what those contain.</p>

<h2>Children</h2>
<p>This is a general news site and is not directed at children under 13, and we do
not knowingly collect information from them.</p>

<h2>Changes</h2>
<p>If this policy changes in a way that matters, the change will be dated here.</p>
"""
    prose_page("privacy.html", "about", "Privacy",
               "What Gospel News Access does and does not collect about its readers.",
               body, 0, [("Front Page", SITE + "/"), ("Privacy", SITE + "/privacy.html")])


# ---------------------------------------------------------------------------
# ORIGINAL REPORTING
#
# The wire keeps the site alive; originals make it a publication.
# data/originals.json starts EMPTY and that is correct — we will not invent a
# story to demonstrate the feature. Each real story added there renders to
# /story/<slug>.html with proper NewsArticle markup, a real dateline, a real
# timestamp, and any corrections printed inline at the bottom.
# ---------------------------------------------------------------------------
def originals() -> list[dict]:
    doc = g.read_json("data/originals.json", {"articles": []}) or {"articles": []}
    arts = [a for a in doc.get("articles", []) if a.get("status") == "published"]
    arts.sort(key=lambda a: a.get("published", ""), reverse=True)
    return arts


def render_originals() -> list[dict]:
    arts = originals()
    for a in arts:
        now = g.now_utc()
        pub = g.parse_dt(a["published"]) or now
        byline = a.get("byline") or "Gospel News Access Staff"
        dateline_bits = [x for x in [a.get("dateline"), pub.astimezone(g.PACIFIC).strftime("%B %-d, %Y at %-I:%M %p Pacific")] if x]
        body_html = "".join("<p>%s</p>" % g.esc(p) for p in a.get("body", []))

        # Corrections print inline at the bottom of the corrected story, dated.
        corr_html = ""
        if a.get("corrections"):
            items = "".join(
                "<p><strong>Correction, %s:</strong> %s</p>"
                % (g.esc(x.get("date", "")), g.esc(x.get("text", "")))
                for x in a["corrections"])
            corr_html = ('<div class="note note--warn"><h3>Corrections</h3>%s'
                         '<p>Our full <a href="../corrections.html">corrections '
                         'policy</a>.</p></div>' % items)

        img_html = ""
        if a.get("image"):
            img_html = ('<figure class="hero__fig"><img src="%s" alt="%s">'
                        '<figcaption class="hero__credit">%s</figcaption></figure>'
                        % (g.esc(a["image"]), g.esc(a.get("image_alt", "")),
                           g.esc(a.get("image_credit", ""))))

        body = f"""<h1>{g.esc(a['title'])}</h1>
<p class="lede">{g.esc(a.get('standfirst',''))}</p>
<p class="dateline">{g.esc(' &middot; '.join(dateline_bits))} &middot; By {g.esc(byline)}</p>
{img_html}
{body_html}
{corr_html}
"""
        prose_page("story/%s.html" % a["slug"], "news", a["title"],
                   a.get("standfirst") or a["title"], body, 1,
                   [("Front Page", SITE + "/"), ("News", SITE + "/news.html"),
                    (a["title"], "%s/story/%s.html" % (SITE, a["slug"]))],
                   [article_schema(a)])
    return arts


# ---------------------------------------------------------------------------
# Sitemaps, robots, RSS, 404
# ---------------------------------------------------------------------------
STATIC_PAGES = [
    ("index.html", "hourly", "1.0"),
    ("news.html", "hourly", "0.9"),
    ("music.html", "hourly", "0.8"),
    ("charts.html", "weekly", "0.9"),
    ("charts/methodology.html", "monthly", "0.7"),
    ("charts/panel.html", "weekly", "0.6"),
    ("submit-music.html", "monthly", "0.7"),
    ("video.html", "daily", "0.7"),
    ("cdc/index.html", "monthly", "0.6"),
    ("cdc/gospel-news-access.html", "monthly", "0.6"),
    ("cdc/his-presence-fire.html", "monthly", "0.6"),
    ("churches.html", "weekly", "0.7"),
    ("churches/join.html", "monthly", "0.5"),
    ("about.html", "monthly", "0.6"),
    ("contact.html", "monthly", "0.5"),
    ("masthead.html", "monthly", "0.5"),
    ("corrections.html", "monthly", "0.5"),
    ("privacy.html", "yearly", "0.3"),
]


def render_sitemaps(arts: list[dict]) -> None:
    today = g.now_utc().strftime("%Y-%m-%d")
    urls = []
    for path, freq, pri in STATIC_PAGES:
        loc = SITE + "/" + ("" if path == "index.html" else path)
        urls.append("  <url><loc>%s</loc><lastmod>%s</lastmod>"
                    "<changefreq>%s</changefreq><priority>%s</priority></url>"
                    % (g.esc(loc), today, freq, pri))
    for a in arts:
        urls.append("  <url><loc>%s/story/%s.html</loc><lastmod>%s</lastmod>"
                    "<changefreq>monthly</changefreq><priority>0.8</priority></url>"
                    % (SITE, g.esc(a["slug"]), g.esc((a.get("updated") or a["published"])[:10])))
    g.write_text("sitemap.xml",
                 '<?xml version="1.0" encoding="UTF-8"?>\n'
                 '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
                 + "\n".join(urls) + "\n</urlset>\n")

    # --- Google News sitemap: ONLY our own articles, only the last 48 hours ---
    # A Google News sitemap describes pages WE published. Wire headlines belong
    # to other publishers and must never appear here — submitting somebody
    # else's reporting as our own is how a publisher gets removed from Google
    # News entirely.
    cutoff = g.now_utc() - timedelta(hours=48)
    recent = [a for a in arts if (g.parse_dt(a["published"]) or g.now_utc()) >= cutoff]
    news_urls = []
    for a in recent:
        news_urls.append(
            "  <url><loc>%s/story/%s.html</loc>\n"
            "    <news:news><news:publication>"
            "<news:name>Gospel News Access</news:name>"
            "<news:language>en</news:language></news:publication>\n"
            "    <news:publication_date>%s</news:publication_date>\n"
            "    <news:title>%s</news:title></news:news></url>"
            % (SITE, g.esc(a["slug"]), g.esc(a["published"]), g.esc(a["title"])))
    g.write_text(
        "sitemap-news.xml",
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<!-- Google News sitemap. Holds only Gospel News Access original\n'
        '     reporting published in the last 48 hours. Aggregated wire\n'
        '     headlines belong to their original publishers and are\n'
        '     deliberately never listed here. -->\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"\n'
        '        xmlns:news="http://www.google.com/schemas/sitemap-news/0.9">\n'
        + ("\n".join(news_urls) + "\n" if news_urls else "")
        + "</urlset>\n")

    g.write_text("robots.txt",
                 "# Gospel News Access\n"
                 "User-agent: *\n"
                 "Allow: /\n\n"
                 "# Our own reporting, for Google News\n"
                 "Sitemap: %s/sitemap.xml\n"
                 "Sitemap: %s/sitemap-news.xml\n" % (SITE, SITE))


def render_feed(arts: list[dict]) -> None:
    """An RSS feed of our OWN reporting only, for the same reason."""
    items = []
    for a in arts[:40]:
        pub = g.parse_dt(a["published"]) or g.now_utc()
        items.append(
            "    <item><title>%s</title>"
            "<link>%s/story/%s.html</link>"
            "<guid isPermaLink=\"true\">%s/story/%s.html</guid>"
            "<pubDate>%s</pubDate>"
            "<description>%s</description></item>"
            % (g.esc(a["title"]), SITE, g.esc(a["slug"]), SITE, g.esc(a["slug"]),
               pub.strftime("%a, %d %b %Y %H:%M:%S +0000"),
               g.esc(a.get("standfirst", ""))))
    g.write_text("feed.xml",
                 '<?xml version="1.0" encoding="UTF-8"?>\n'
                 '<rss version="2.0"><channel>\n'
                 '    <title>Gospel News Access</title>\n'
                 '    <link>%s/</link>\n'
                 '    <description>Original gospel, Christian and faith reporting '
                 'from Gospel News Access.</description>\n'
                 '    <language>en-us</language>\n'
                 '    <lastBuildDate>%s</lastBuildDate>\n%s\n'
                 '</channel></rss>\n'
                 % (SITE, g.now_utc().strftime("%a, %d %b %Y %H:%M:%S +0000"),
                    "\n".join(items)))


def render_404() -> None:
    body = """<h1>That page is not here</h1>
<p class="lede">The link may be old, or we may have moved something.</p>
<ul>
<li><a href="/gospel-news-access/">The front page</a></li>
<li><a href="/gospel-news-access/news.html">The news wire</a></li>
<li><a href="/gospel-news-access/charts.html">The GNA charts</a></li>
<li><a href="/gospel-news-access/contact.html">Contact us</a></li>
</ul>
"""
    html = [L.head("Page not found", "That page could not be found.", SITE + "/404.html", 0),
            L.header(0), L.nav("", 0),
            '<main id="main" class="wrap"><div class="prose">', body, "</div></main>",
            L.footer(0)]
    g.write_text("404.html", "".join(html))


# ---------------------------------------------------------------------------
def render_all() -> None:
    """Rebuild every page. Safe to run at any time."""
    render_index()
    render_news()
    render_music()
    render_video()
    render_charts()
    render_methodology()
    render_panel()
    render_submit_music()
    render_cdc()
    render_churches()
    render_eeat()
    arts = render_originals()
    render_sitemaps(arts)
    render_feed(arts)
    render_404()


if __name__ == "__main__":
    render_all()
    print("Rendered all pages.")
