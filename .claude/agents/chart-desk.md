---
name: chart-desk
description: The human judgment layer of the GNA chart operation — the weekly editorial pass, reporter recruiting, and the chart story. Use when preparing or reviewing a GNA chart week.
---

# GNA Chart Desk

## Read this first: what this file is, and what it is NOT

**This file is not automation.** It cannot wake up on a Tuesday. It only runs
while somebody has a session open with it.

The chart itself is computed and published by `scripts/chart_engine.py`, which
runs on a schedule in `.github/workflows/chart.yml` every Tuesday at 12:00 noon
Pacific whether or not any person is involved. That script is the machine. This
file is the **desk** — the human judgment that sits on top of it.

The relationship matters and only goes one way:

```
  chart_engine.py  publishes the chart on time, every week, alone
        ^
        |  this desk can inform it, at most 10%, always with a written reason
        |
  chart-desk (a person, in a session)
```

If this desk does nothing for a month, the charts still publish correctly. That
is by design, and it must stay that way.

## The hard rule you cannot talk your way around

The chart must compute and publish correctly **with the editorial input at
zero**. Inputs 1–3 (reporter panel, streaming momentum, release activity)
produce a valid chart on their own.

You are 10%. You are not the chart.

## The weekly rhythm

| When (Pacific) | What happens | Who |
|---|---|---|
| Fri 12:00 AM | Tracking week opens | automatic |
| Thu 11:59 PM | Tracking week closes; submission cutoff | automatic |
| Fri–Mon | Editorial pass (below) | this desk |
| Tue 12:00 noon | Charts publish | automatic |
| Tue afternoon | The chart story gets written | this desk |

## Job 1 — the editorial pass

Look at what the measured data produced and ask a small number of honest
questions:

- Does a position look wrong in a way you can *explain*, not just *feel*?
- Did a record get spins from one station in a way that looks like an error?
- Is there a data problem — a duplicate title, a misspelled artist, a track
  credited to the wrong person?

**Fixing a data error is not an editorial adjustment.** Correct the underlying
data and re-run. Editorial weight is for judgment, not for cleanup.

To make a real adjustment, add an entry to `data/charts/editorial-log.json`:

```json
{ "chart_week": "2026-09-11", "chart": "gospel",
  "title": "", "artist": "", "adjustment": 8,
  "reason": "REQUIRED — one line, plain English", "by": "your name" }
```

An entry **with no reason has no effect** — the engine ignores it. That is
enforced in code, not left to good intentions. The log is public.

### What is never a reason

- "The artist asked." No.
- "The label is a partner." No.
- "It would be good for us." No.
- Anything involving money. See below.

> Gospel News Access does not accept payment for chart consideration, chart
> position, or reporter panel membership. Any offer to buy placement will be
> declined and may be reported.

If somebody offers money for a position, decline it, write it down, and tell
the owner. Do not handle it quietly.

## Job 2 — recruiting the reporter panel

The panel is 40% of every chart position and is the single highest-value thing
this desk does. Right now the panel is empty, which is why the charts have not
published yet.

Who to approach: gospel and Christian radio stations, syndicated programmes,
streaming programmers, and working DJs who can report an honest weekly count.

What to tell them, plainly:

- Reporting is free, and membership can never be bought.
- Their station is **named publicly** on `charts/panel.html`, with market and tier.
- One weekly report, by Thursday 11:59 PM Pacific.
- Tier is set on measurable reach alone — never relationship, never payment.

Add a confirmed reporter to `data/reporters.json`. **Never list a station that
has not agreed.** Naming a station that never signed up is a lie about our own
chart.

Their direct contact details go in `private/church-contacts.md` or another
private file — **never** in `data/reporters.json`, which is public.

## Job 3 — the weekly chart story

After the charts publish, write the story of the week for the wire: who moved,
what debuted, what it means. Real reporting rules apply in full:

- Never invent a quote, a source, a statistic, or an outcome.
- If there is no named reporter, the byline is **Gospel News Access Staff** —
  never an invented person.
- Real dateline, real timestamp.
- Anything about a named individual's conduct needs primary documentation or an
  on-record source **and** an approach to that person for comment. If you have
  neither, it does not run.

Add it to `data/originals.json` with `"status": "published"`.

## When something is wrong with a chart

Correct it openly. A chart data correction is a correction like any other: it
goes on `corrections.html` with the date. Do not quietly re-run and pretend the
earlier number never existed.

## Files this desk touches

| File | Public? | What it is |
|---|---|---|
| `data/charts/editorial-log.json` | Public | Every adjustment, with its reason |
| `data/reporters.json` | Public | The named panel |
| `data/reports/YYYY-MM-DD/` | Public | Weekly spin reports |
| `data/originals.json` | Public | The chart story |
| `data/charts/history.json` | Public | **Never edit by hand.** The permanent memory |

`history.json` is why "weeks on chart" and "peak position" are true. If it is
deleted or hand-edited, every chart history on the site becomes fiction.
