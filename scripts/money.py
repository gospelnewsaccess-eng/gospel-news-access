"""
money.py — the Advertise (media kit) page and the Privacy & ads page.

Plain English: these two pages are how Gospel News Access earns money honestly.
The Advertise page lists what a church, label, ministry or brand can buy, at
starting rates, and promises that paid content is always labeled and never buys
coverage or chart position. The Privacy page tells readers, in plain words, that
Google may show ads using cookies, how to turn personalized ads off, and how
affiliate links and sponsored content are disclosed. Google requires that
disclosure before ads can run; without it the AdSense account can be refused.

render_site.py calls render_money(), which writes advertise.html and
privacy.html. The shared sections are the same on every site in the Newswire
Hollywood media group; the Gospel News Access details are at the bottom.
"""

CSS = """.mk{max-width:1000px;margin:0 auto;padding:0 18px 12px;overflow-wrap:break-word}
.mk *{box-sizing:border-box}
.mk-hero{padding:34px 0 22px;border-bottom:3px solid var(--mk-i)}
.mk-kick{display:inline-block;font-family:var(--mk-h);font-weight:700;font-size:11.5px;letter-spacing:.16em;text-transform:uppercase;color:var(--mk-a)}
.mk h1{font-family:var(--mk-h);font-weight:700;font-size:clamp(30px,6.5vw,52px);line-height:1.04;color:var(--mk-i);margin:10px 0 12px;letter-spacing:-.4px}
.mk-lede{font-size:clamp(17px,2.4vw,19.5px);line-height:1.5;max-width:42em;margin:0}
.mk h2{font-family:var(--mk-h);font-weight:700;font-size:clamp(21px,4vw,28px);line-height:1.15;color:var(--mk-i);border-bottom:2px solid var(--mk-i);padding-bottom:7px;margin:40px 0 14px}
.mk h3{font-family:var(--mk-h);font-weight:700;font-size:19px;line-height:1.2;color:var(--mk-i);margin:22px 0 8px}
.mk p{margin:0 0 14px;max-width:46em;line-height:1.6}
.mk ul.mk-list{margin:0 0 16px;padding-left:20px}
.mk ul.mk-list li{margin-bottom:8px;line-height:1.55}
.mk a.inl{color:var(--mk-a);text-decoration:underline;text-underline-offset:2px}
.mk-grid{display:grid;grid-template-columns:1fr;gap:16px;margin-top:6px}
@media(min-width:640px){.mk-grid{grid-template-columns:1fr 1fr}}
@media(min-width:980px){.mk-grid{grid-template-columns:repeat(3,1fr)}}
.mk-card{border:1px solid var(--mk-r);border-top:4px solid var(--mk-a);background:var(--mk-c);padding:18px 18px 16px;display:flex;flex-direction:column;gap:9px;min-width:0}
.mk-card h3{margin:0}
.mk-price{font-family:var(--mk-h);font-weight:800;font-size:31px;line-height:1;color:var(--mk-a)}
.mk-price small{font-size:13px;font-weight:600;color:var(--mk-m);letter-spacing:.03em;margin-left:5px}
.mk-from{display:block;font-family:var(--mk-h);font-size:10.5px;letter-spacing:.15em;text-transform:uppercase;color:var(--mk-m);font-weight:700;margin-bottom:5px}
.mk-card p{font-size:15px;line-height:1.5;margin:0}
.mk-tag{align-self:flex-start;font-family:var(--mk-h);font-weight:700;font-size:10.5px;letter-spacing:.12em;text-transform:uppercase;background:var(--mk-s);color:var(--mk-i);padding:5px 8px;border:1px solid var(--mk-r);margin-top:auto}
.mk-tiers{list-style:none;margin:2px 0 0;padding:0}
.mk-tiers li{display:flex;justify-content:space-between;align-items:baseline;gap:10px;border-top:1px solid var(--mk-r);padding:8px 0 7px;font-size:14.5px;line-height:1.35}
.mk-tiers b{font-family:var(--mk-h);color:var(--mk-a);font-size:17px;white-space:nowrap}
.mk-note{background:var(--mk-s);border-left:4px solid var(--mk-a);padding:14px 16px;margin:18px 0;font-size:15.5px;line-height:1.55}
.mk-note p:last-child{margin-bottom:0}
.mk-steps{counter-reset:s;list-style:none;margin:0 0 10px;padding:0;display:grid;gap:14px}
.mk-steps li{counter-increment:s;position:relative;padding-left:46px;line-height:1.55;min-height:32px}
.mk-steps li::before{content:counter(s);position:absolute;left:0;top:-2px;width:32px;height:32px;border-radius:50%;background:var(--mk-a);color:var(--mk-onA);font-family:var(--mk-h);font-weight:700;font-size:15px;line-height:32px;text-align:center}
.mk-promise{display:grid;grid-template-columns:1fr;gap:12px;list-style:none;margin:0;padding:0}
@media(min-width:700px){.mk-promise{grid-template-columns:1fr 1fr}}
.mk-promise li{border:1px solid var(--mk-r);background:var(--mk-c);padding:14px 16px;line-height:1.5;font-size:15.5px}
.mk-promise b{display:block;font-family:var(--mk-h);color:var(--mk-i);font-size:16.5px;margin-bottom:3px}
.mk-contact{border:2px solid var(--mk-i);background:var(--mk-c);padding:20px;margin:30px 0 8px;display:flex;flex-wrap:wrap;gap:14px 28px;align-items:center;justify-content:space-between}
.mk-contact .k{display:block;font-family:var(--mk-h);font-weight:700;font-size:11px;letter-spacing:.15em;text-transform:uppercase;color:var(--mk-m);margin-bottom:7px}
.mk-contact .mail{font-family:var(--mk-h);font-weight:700;font-size:clamp(18px,4.6vw,25px);color:var(--mk-a);word-break:break-word;text-decoration:none}
.mk-contact p{margin:6px 0 0;font-size:14.5px;color:var(--mk-m)}
.mk-btn{display:inline-block;background:var(--mk-a);color:var(--mk-onA);font-family:var(--mk-h);font-weight:700;font-size:14px;letter-spacing:.06em;text-transform:uppercase;padding:13px 18px;border-radius:3px;text-decoration:none;white-space:nowrap}
.mk-btn:hover{filter:brightness(1.08)}
.mk-btns{display:flex;flex-wrap:wrap;gap:10px}
.mk-fine{font-size:13.5px;color:var(--mk-m);line-height:1.5}
.mk-toc{display:flex;flex-wrap:wrap;gap:8px;margin:18px 0 0;padding:0;list-style:none}
.mk-toc a{display:inline-block;border:1px solid var(--mk-r);padding:6px 11px;font-family:var(--mk-h);font-size:13px;font-weight:600;color:var(--mk-i);text-decoration:none;background:var(--mk-c)}
.mk-toc a:hover{border-color:var(--mk-a);color:var(--mk-a)}"""


def css(v):
    """v: dict of a (accent), onA, i (headings), r (rules), s (soft bg),
    c (card bg), m (muted), h (heading font)."""
    return (".mk{--mk-a:%(a)s;--mk-onA:%(onA)s;--mk-i:%(i)s;--mk-r:%(r)s;--mk-s:%(s)s;"
            "--mk-c:%(c)s;--mk-m:%(m)s;--mk-h:%(h)s}\n" % v) + CSS


def _card(title, price, unit, body, label, starting=True):
    return ('<div class="mk-card"><h3>%s</h3><div><span class="mk-from">%s</span>'
            '<span class="mk-price">%s<small>%s</small></span></div><p>%s</p>'
            '<span class="mk-tag">Labeled: %s</span></div>'
            % (title, "Starting rate" if starting else "From", price, unit, body, label))


def advertise(site):
    """site keys: name, short, audience (html paragraphs), reach (html list items),
    channels (text e.g. 'Facebook and Instagram'), pr_tiers (list of (name, desc, price)) or None,
    contact (html for the contact card), extra_promise (optional html li),
    privacy_href, pressroom_href."""
    n = site["name"]
    cards = [
        _card("Homepage takeover / banner", "$250", "/ week",
              "Your banner across the top of our homepage for seven days, linked to your page or tickets. "
              "Creative supplied by you, or designed with our desk.", "Advertisement"),
        _card("Sponsored article", "$350", "/ article",
              "A story about your release, launch, event or brand, written with our desk in our house style, "
              "published on %s with a permanent link, then pushed to our Facebook and Instagram." % n,
              "Sponsored"),
        _card("Sponsored social post package", "$150", "/ package",
              "A post built for our Facebook and Instagram audiences, with your link and handles, labeled #ad "
              "on every platform.", "#ad"),
        ('<div class="mk-card"><h3>Event &amp; brand partnerships</h3><div><span class="mk-from">Packages from</span>'
         '<span class="mk-price">$1,000</span></div><p>Premieres, galas, album and product launches, tours and festivals: '
         'a package built around your date, combining banner placement, sponsored coverage, on-site content and social. '
         'Content rights and affiliate options can be built in.</p><span class="mk-tag">Labeled: Sponsored / Partner</span></div>'),
    ]
    if site.get("pr_tiers"):
        tiers = "".join('<li><span>%s<br><span class="mk-fine">%s</span></span><b>%s</b></li>' % t
                        for t in site["pr_tiers"])
        cards.append('<div class="mk-card"><h3>Press-release distribution</h3><div><span class="mk-from">Per release</span>'
                     '<span class="mk-price">%s<small>and up</small></span></div><ul class="mk-tiers">%s</ul>'
                     '<span class="mk-tag">Labeled: Press release</span></div>'
                     % (site["pr_tiers"][0][2], tiers))
    else:
        cards.append(_card("Press-release distribution", "$99", "/ release",
                           "Your announcement published on %s in its own clearly labeled press-release format, "
                           "with a permanent link you can share." % n, "Press release"))
    cards.append('<div class="mk-card"><h3>Something bigger?</h3><div><span class="mk-from">Custom</span>'
                 '<span class="mk-price">Let&rsquo;s talk</span></div><p>Branded series, newsletter and video sponsorship, '
                 'content licensing and multi-site packages across the Newswire Hollywood media group.</p>'
                 '<span class="mk-tag">Always labeled</span></div>')

    return """<div class="mk">
<div class="mk-hero">
<span class="mk-kick">Advertise &middot; Media kit</span>
<h1>Advertise with %(name)s</h1>
<p class="mk-lede">%(lede)s</p>
<ul class="mk-toc"><li><a href="#audience">Audience</a></li><li><a href="#rates">Formats &amp; rates</a></li><li><a href="#book">How to book</a></li><li><a href="#promise">Our promise</a></li><li><a href="#contact">Contact</a></li></ul>
</div>

<h2 id="audience">Who you reach</h2>
%(audience)s
<ul class="mk-list">
%(reach)s
</ul>
<div class="mk-note"><p><b>Audience figures available on request.</b> We share current traffic and social numbers directly with advertisers rather than printing round numbers here, so what you see is current and verifiable.</p></div>

<h2 id="rates">Formats &amp; starting rates</h2>
<p>Every price below is a <b>starting rate</b> in US dollars. Your final quote depends on dates, scope and placement, and is confirmed in writing before anything runs.</p>
<div class="mk-grid">
%(cards)s
</div>
<p class="mk-fine" style="margin-top:14px">Every campaign ends with a short report: live links to everything that ran, dates, and placement. Multi-week and multi-format bookings are quoted as a package.</p>

<h2 id="book">How to book</h2>
<ol class="mk-steps">
<li><b>Tell us what you need.</b> The format, your dates, and a link to what you are promoting.</li>
<li><b>We confirm and invoice.</b> We check the dates, confirm the package and price in writing, and send an invoice.</li>
<li><b>We publish and report.</b> Once the invoice is paid, your placement goes live on schedule and you receive the live links.</li>
</ol>

<h2 id="promise">Our promise to readers and advertisers</h2>
<ul class="mk-promise">
<li><b>Paid content is always labeled.</b> Sponsored articles say &ldquo;Sponsored&rdquo;, banners say &ldquo;Advertisement&rdquo;, releases say &ldquo;Press release&rdquo;, and paid social posts carry #ad.</li>
<li><b>Advertisers never direct coverage.</b> Buying an ad or a sponsored post does not buy, change or stop a news story. Our newsroom decides what it covers.</li>
<li><b>No ads inside paid stories.</b> We do not place third-party ads inside the text of a sponsored article or a client&rsquo;s press release.</li>
<li><b>Affiliate links are disclosed.</b> Where we may earn a commission, the link is marked as sponsored and the page says so. See our <a class="inl" href="%(privacy)s">privacy &amp; ads policy</a>.</li>
%(extra_promise)s</ul>

<div class="mk-contact" id="contact">
%(contact)s
</div>
<p class="mk-fine">Payment: we confirm and invoice. Press releases can also be submitted through our <a class="inl" href="%(pressroom)s">Press Room</a>.</p>
</div>""" % {
        "name": n, "lede": site["lede"], "audience": site["audience"], "reach": site["reach"],
        "cards": "\n".join(cards), "privacy": site.get("privacy_href", "privacy.html"),
        "pressroom": site.get("pressroom_href", "pressroom.html"),
        "extra_promise": site.get("extra_promise", ""), "contact": site["contact"],
    }


def privacy(site):
    """site keys: name, domain, extra (html sections specific to the site),
    contact_line (html), updated (text)."""
    return """<div class="mk">
<div class="mk-hero">
<span class="mk-kick">Privacy &amp; ads</span>
<h1>Privacy, cookies and advertising</h1>
<p class="mk-lede">What %(name)s does and does not know about you, how advertising on this site works, and how we label anything someone paid for. In plain English. Last updated %(updated)s.</p>
</div>

<h2>The short version</h2>
<p>%(name)s is a news website. There are no reader accounts and no logins, and we do not sell personal information. When advertising is running on the site, Google and its partners may use cookies to show ads. Anything a client paid for is labeled.</p>

<h2 id="ads">Advertising and cookies</h2>
<p>We may show ads from Google and its advertising partners. Third-party vendors, including Google, use cookies to serve ads based on your prior visits to this website or to other websites. Google&rsquo;s use of advertising cookies enables it and its partners to serve ads to you based on your visits to this site and other sites on the internet.</p>
<ul class="mk-list">
<li>How Google uses this information: <a class="inl" href="https://policies.google.com/technologies/partner-sites" target="_blank" rel="noopener">How Google uses information from sites or apps that use our services</a>.</li>
<li>You can turn off personalized advertising at any time in Google&rsquo;s <a class="inl" href="https://adssettings.google.com" target="_blank" rel="noopener">Ads Settings</a>, and opt out of many other vendors&rsquo; personalized ads at <a class="inl" href="https://www.aboutads.info/choices/" target="_blank" rel="noopener">aboutads.info</a>.</li>
<li>Visitors in the European Economic Area, the United Kingdom and Switzerland are asked for consent through Google&rsquo;s consent message before personalized ads are shown.</li>
<li>You can also block or delete cookies in your browser settings. The site still works without them.</li>
</ul>
<p>We do not place third-party ads inside the text of sponsored articles or clients&rsquo; press releases.</p>

<h2 id="affiliate">Affiliate links</h2>
<p>Some links to products, tickets, music or services may be affiliate links. If you buy something through one, we may earn a commission, at no extra cost to you. Affiliate links are marked <code>rel="sponsored"</code> in the page code and disclosed on the page where they appear. A commission never decides what we cover or how we cover it.</p>

<h2 id="sponsored">Sponsored content is always labeled</h2>
<p>Anything a client paid for says so where you can see it: sponsored articles carry a &ldquo;Sponsored&rdquo; label, banners say &ldquo;Advertisement&rdquo;, press releases are labeled as press releases, and paid social posts carry #ad. Advertisers never direct our news coverage. Details for advertisers are on our <a class="inl" href="advertise.html">Advertise</a> page.</p>

<h2>Photographs, video and links out</h2>
<p>Headline cards from other outlets display that outlet&rsquo;s own photo from its own servers, so when a page loads, that publisher&rsquo;s server can see your IP address, the same as if you visited their site. Embedded videos come from YouTube; once you press play, YouTube&rsquo;s privacy policy applies to that playback. When you follow a link to another publication, you are on their site under their privacy policy.</p>
%(extra)s
<h2>Hosting</h2>
<p>This site is served by GitHub Pages. GitHub keeps its own server logs, as any web host does; see GitHub&rsquo;s privacy statement for what those contain.</p>

<h2>Children</h2>
<p>This is a general news site. It is not directed at children under 13, and we do not knowingly collect information from them.</p>

<h2>Questions and changes</h2>
<p>%(contact_line)s If this policy changes in a way that matters, the change is dated here.</p>
</div>""" % site


# ---------------------------------------------------------------------------
# Gospel News Access
# ---------------------------------------------------------------------------
import sys  # noqa: E402

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import gnalib as g  # noqa: E402
import layout as L  # noqa: E402

FB = "https://www.facebook.com/profile.php?id=100069397881039"
IG = "https://www.instagram.com/gospelnewsaccess/"


def _contact(org: dict) -> tuple[str, str]:
    """The advertising contact card, and the one-line contact for the privacy
    page. Uses a real inbox from data/site-config.json when one is set
    (email_advertising, else email_general); until then, our social inboxes.
    Never an invented address."""
    email = org.get("email_advertising") or org.get("email_general")
    if email:
        e = g.esc(email)
        card = ('<div><span class="k">Advertising &amp; partnerships</span>'
                '<a class="mail" href="mailto:%s?subject=Advertising%%20enquiry">%s</a>'
                '<p>Tell us the format, your dates and what you are promoting. We reply with '
                'availability and a quote.</p></div><div class="mk-btns"><a class="mk-btn" '
                'href="mailto:%s?subject=Advertising%%20enquiry">Email us</a></div>' % (e, e, e))
        line = ('Questions about this policy or an ad you saw here: email '
                '<a class="inl" href="mailto:%s">%s</a>.' % (e, e))
        return card, line
    card = ('<div><span class="k">Advertising &amp; partnerships</span><span class="mail">Message us</span>'
            '<p>Our advertising inbox is being set up. Until it is live, send Gospel News Access a message '
            'on Facebook or Instagram with the format, your dates and what you are promoting, and we reply '
            'with availability and a quote.</p></div><div class="mk-btns">'
            '<a class="mk-btn" href="%s" target="_blank" rel="noopener">Message on Facebook</a>'
            '<a class="mk-btn" href="%s" target="_blank" rel="noopener">Message on Instagram</a></div>' % (FB, IG))
    line = ('Questions about this policy or an ad you saw here: message Gospel News Access on '
            '<a class="inl" href="%s" target="_blank" rel="noopener">Facebook</a> or '
            '<a class="inl" href="%s" target="_blank" rel="noopener">Instagram</a>, or see our '
            '<a class="inl" href="contact.html">contact page</a>.' % (FB, IG))
    return card, line


SITE = dict(
    name="Gospel News Access",
    lede="Gospel News Access is the gospel, Christian and faith news wire: top faith news, gospel music, "
         "the GNA Charts, video, community development and a public church directory, updated continuously. "
         "Put your ministry, release, conference or brand in front of the faith community.",
    audience="<p>Our readers are gospel and Christian music fans, churchgoers, pastors and ministry leaders, "
             "choirs and worship teams, and the labels, promoters and organizations that serve them. They come "
             "for faith news, new music, the GNA Charts, video and the church directory.</p>",
    reach="<li><b>On the site:</b> the news wire, music, the GNA Charts, video, community development and the church directory.</li>\n"
          "<li><b>On social:</b> Facebook, Instagram, Threads and YouTube.</li>\n"
          "<li><b>Across the network:</b> package deals can run alongside Newswire Hollywood (the business of entertainment), "
          "Hollywood News Access (celebrity and pop culture) and World Newswire Press (global news).</li>",
    pr_tiers=None,
    extra_promise="<li><b>Charts and coverage are never for sale.</b> Gospel News Access does not accept payment for "
                  "news coverage, for chart consideration or for chart position. Advertising buys a labeled placement, "
                  "nothing more.</li>\n",
)

PRIVACY_EXTRA = """<h2>Forms</h2>
<p>When form submission is switched on, we use what you send only for the purpose you sent it: to consider your music, to list your church, or to answer you. Contact details supplied through a form are never published and never sold. You may ask us to delete anything you have sent, and we will.</p>
"""

# Dark-theme colours from assets/css/gna.css.
COLORS = dict(a="#f0b429", onA="#0a0a0c", i="#ffffff", r="#2a2a34", s="#1b1b22", c="#121217",
              m="#a8a8b4", h='-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif')


def _page(path: str, nav_key: str, title: str, description: str, body: str, crumbs) -> None:
    url = L.SITE + "/" + path
    html = [
        L.head(title, description, url, 0, [L.breadcrumbs(crumbs)]),
        L.header(0),
        L.nav(nav_key, 0),
        '<main id="main" class="wrap">',
        body,
        "</main>",
        L.footer(0),
    ]
    g.write_text(path, "".join(html))


def render_money(org: dict) -> None:
    card, line = _contact(org)
    site = dict(SITE, contact=card)
    _page("advertise.html", "advertise", "Advertise with Gospel News Access",
          "Advertise with Gospel News Access: homepage takeovers, sponsored articles, social packages, "
          "partnerships and press-release distribution. Starting rates and how to book.",
          advertise(site), [("Front Page", L.SITE + "/"), ("Advertise", L.SITE + "/advertise.html")])
    _page("privacy.html", "about", "Privacy, Cookies & Advertising",
          "How Gospel News Access handles privacy, cookies, Google advertising, affiliate links and "
          "sponsored content.",
          privacy(dict(name="Gospel News Access", domain="gospelnewsaccess.com", updated="November 22, 2026",
                       extra=PRIVACY_EXTRA, contact_line=line)),
          [("Front Page", L.SITE + "/"), ("Privacy", L.SITE + "/privacy.html")])
