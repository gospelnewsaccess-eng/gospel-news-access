# Gospel News Access

An automated gospel, Christian and faith news wire — top faith news that updates
itself with photos and video, a music section with our own charts, a community
development center section, and a public church directory.

**Live site:** https://gospelnewsaccess-eng.github.io/gospel-news-access/

---

## How this works, in plain English

The site is plain HTML and CSS. There is no framework and no build step — a web
browser can open any page in this repository directly.

The pages that change on their own are **written by Python scripts** that run on
a schedule on GitHub's computers (GitHub Actions). Nobody has to be logged in.
Nobody has to be awake. The schedule runs, the script fetches the news, rewrites
the HTML files, and commits them to `main`. GitHub Pages then serves `main`.

That is the whole machine:

```
  a schedule fires  ->  a Python script runs  ->  it writes HTML
        ->  it commits to main  ->  GitHub Pages serves the new page
```

## What each moving part does, and what breaks without it

| Part | What it is | What breaks if it is missing |
|---|---|---|
| `scripts/wire.py` | Fetches every news feed, pulls a photo for each story, writes the front page and the wire | The site stops updating. It becomes a brochure. |
| `scripts/verify_feeds.py` | Checks that every feed URL is real and currently publishing | Dead feeds sit in the list silently and the wire quietly thins out |
| `scripts/video.py` | Fetches YouTube channel feeds, builds the video wall | The video page renders empty (by design, not broken) |
| `scripts/chart_engine.py` | Computes the four GNA charts and updates chart history | Charts freeze. "Weeks on chart" stops being true. |
| `scripts/render_site.py` | Turns stored data into every HTML page | Nothing renders at all |
| `data/charts/history.json` | The permanent memory of every chart run | Peak position and weeks-on-chart become fiction |
| `.github/workflows/*.yml` | The schedules | Scripts exist but never run. Nothing is automatic. |

## Why scripts and not agent instructions

An agent instruction file only runs while somebody has a session open. It cannot
wake up at 6am on a Tuesday. Anything that must happen on its own is a Python
script on a schedule. The one agent file in this repo,
`.claude/agents/chart-desk.md`, is deliberately *not* automation — it describes
the human judgment layer that sits on top of the script.

## Security rules that are not negotiable

1. No API key, token or password in any file, ever. GitHub Secrets only.
2. `private/` is never published.
3. No Zoom meeting ID, dial-in code or password on any public page.
4. Nothing is invented — not a person, quote, statistic, phone number, address,
   program or partner. Missing facts are marked TODO and render as nothing.

## Repository map

```
index.html  news.html  music.html  video.html  churches.html
about.html  contact.html  masthead.html  corrections.html  privacy.html
charts.html  submit-music.html
charts/methodology.html   charts/panel.html
cdc/index.html  cdc/gospel-news-access.html  cdc/his-presence-fire.html
churches/join.html

scripts/     the engine
data/        what the engine knows
runbook/     click-by-click instructions for Terry
private/     never published
.github/workflows/   the schedules
```

See `runbook/` for step-by-step setup instructions written for someone who has
never used these tools before.
