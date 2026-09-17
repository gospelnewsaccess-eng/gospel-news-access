#!/usr/bin/env python3
"""
chart_engine.py — computes and publishes the four GNA charts.

Plain English: once a week this script adds up everything we measured, ranks
it, compares it to last week, and writes the result into a file that it never
throws away. Then it rebuilds the chart pages.

THE FOUR CHARTS
  GNA Gospel 20      20 slots
  GNA Christian 20   20 slots
  GNA Albums 20      20 slots
  What's Hot         10 slots, fastest movers only

WHAT GOES INTO A POSITION (all of it published on charts/methodology.html)
  40%  reporter panel      — spins reported by named stations, tier-weighted
  35%  streaming momentum  — week-over-week CHANGE, never cumulative totals
  15%  release activity    — new releases and submissions
  10%  editorial desk      — human judgement, every change logged with a reason

THE RULE THAT PROTECTS THE CHART FROM US:
  It must compute and publish correctly with the editorial input at ZERO.
  Inputs 1-3 alone produce a valid chart. If no human touches it in a given
  week, it still goes out on time. Any input with no data has its weight
  redistributed across the inputs that do have data.

THE RULE THAT PROTECTS THE CHART'S MEMORY:
  data/charts/history.json PERSISTS. It is never regenerated from scratch.
  "Weeks on chart" and "peak position" only mean something because that file
  carries forward. A script that recomputes history each week is producing
  fiction. If this run fails partway it writes NOTHING and exits loudly,
  leaving last week's history intact.

Usage:  python3 scripts/chart_engine.py [--dry-run] [--force]
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import re
import shutil
import sys
import traceback
from datetime import datetime, timedelta

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import gnalib as g  # noqa: E402

HISTORY = "data/charts/history.json"
EDITORIAL_LOG = "data/charts/editorial-log.json"

CHART_SIZES = {"gospel_20": 20, "christian_20": 20, "albums_20": 20, "whats_hot": 10}
FALLOFF_WEEKS = 20          # off the chart after this long...
FALLOFF_PROTECT_TOP = 10    # ...unless still this high

TIER_WEIGHT = {"A": 1.00, "B": 0.65, "C": 0.35}


# ---------------------------------------------------------------------------
# The tracking week: Friday 12:00 AM Pacific → Thursday 11:59 PM Pacific
# ---------------------------------------------------------------------------
def tracking_week(ref: datetime | None = None) -> tuple[datetime, datetime]:
    """Return the most recently CLOSED tracking week as (start, end) Pacific."""
    ref = ref or g.now_pacific()
    # Thursday is weekday 3. Find the most recent Thursday 23:59 that has passed.
    days_since_thu = (ref.weekday() - 3) % 7
    end = (ref - timedelta(days=days_since_thu)).replace(
        hour=23, minute=59, second=59, microsecond=0)
    if end > ref:
        end -= timedelta(days=7)
    start = (end - timedelta(days=6)).replace(hour=0, minute=0, second=0, microsecond=0)
    return start, end


def norm_key(title: str, artist: str) -> str:
    """One track, one identity, however sloppily it was typed."""
    def clean(s):
        s = (s or "").lower().strip()
        s = re.sub(r"\(.*?\)|\[.*?\]", " ", s)         # (feat. X), [Live]
        s = re.sub(r"\b(feat|ft|featuring|with)\b.*$", " ", s)
        s = re.sub(r"[^a-z0-9]+", " ", s)
        return " ".join(s.split())
    return "%s|%s" % (clean(title), clean(artist))


# ---------------------------------------------------------------------------
# INPUT 1 — the reporter panel (40%)
# ---------------------------------------------------------------------------
def load_reporter_spins(start, end) -> tuple[dict, dict]:
    """
    Read every spin report filed for this tracking week.

    Reports live in data/reports/YYYY-MM-DD/<station>.json where the folder is
    the tracking week's start (Friday). Spins are normalised by station tier
    so a 2-million-listener station and an 8,000-listener station do not both
    count as "one spin". The tiering rule is published on the methodology page.
    """
    roster = {r.get("name"): r for r in
              (g.read_json("data/reporters.json", {}) or {}).get("reporters", [])}
    points, meta = {}, {"reports": 0, "stations": [], "unknown_stations": []}

    folder = os.path.join(g.ROOT, "data", "reports", start.strftime("%Y-%m-%d"))
    for path in sorted(glob.glob(os.path.join(folder, "*.json"))):
        rep = g.read_json(path)
        if not rep:
            continue
        station = rep.get("station") or os.path.basename(path).rsplit(".", 1)[0]
        known = roster.get(station)
        if not known:
            # A report from a station not on the public panel is NOT counted.
            # Every reporter is named publicly; an anonymous report cannot be
            # checked by anyone, so it cannot move a chart.
            meta["unknown_stations"].append(station)
            continue
        tier = (known.get("tier") or "C").strip().upper()[:1]
        weight = TIER_WEIGHT.get(tier, TIER_WEIGHT["C"])
        meta["reports"] += 1
        meta["stations"].append(station)
        for row in rep.get("spins", []):
            key = norm_key(row.get("title", ""), row.get("artist", ""))
            if not key.strip("|"):
                continue
            entry = points.setdefault(key, {"points": 0.0, "title": row.get("title", ""),
                                            "artist": row.get("artist", ""),
                                            "label_or_independent": row.get("label", ""),
                                            "chart": row.get("chart", "gospel")})
            entry["points"] += float(row.get("spins", 0) or 0) * weight
    return points, meta


# ---------------------------------------------------------------------------
# INPUT 2 — streaming and video momentum (35%)
# ---------------------------------------------------------------------------
def load_streaming_momentum() -> tuple[dict, dict]:
    """
    Week-over-week CHANGE from whichever platforms we are permitted to use.

    Every source is currently switched off in data/chart-sources.json because
    its developer terms have not been reviewed. That is deliberate: see the
    note in that file. When all sources are off this returns nothing and the
    35% is redistributed — the chart stays valid.
    """
    conf = g.read_json("data/chart-sources.json", {}) or {}
    enabled = [s for s in conf.get("streaming_sources", []) if s.get("enabled")]
    meta = {"enabled_sources": [s["id"] for s in enabled],
            "disabled_sources": [s["id"] for s in conf.get("streaming_sources", [])
                                 if not s.get("enabled")]}
    if not enabled:
        return {}, meta

    # Each enabled source writes a normalised delta file that this reads.
    # Adapters are added here as sources are cleared for use.
    points = {}
    for src in enabled:
        path = "data/charts/streaming/%s.json" % src["id"]
        doc = g.read_json(path, {}) or {}
        for row in doc.get("deltas", []):
            key = norm_key(row.get("title", ""), row.get("artist", ""))
            if not key.strip("|"):
                continue
            e = points.setdefault(key, {"points": 0.0, "title": row.get("title", ""),
                                        "artist": row.get("artist", ""),
                                        "label_or_independent": row.get("label", ""),
                                        "chart": row.get("chart", "gospel")})
            # CHANGE only. Never a cumulative total — otherwise a 20-year-old
            # classic sits at number one forever and nothing new can chart.
            e["points"] += max(0.0, float(row.get("delta", 0) or 0))
    return points, meta


# ---------------------------------------------------------------------------
# INPUT 3 — release and submission activity (15%)
# ---------------------------------------------------------------------------
def load_release_activity(start, end) -> tuple[dict, dict]:
    points, meta = {}, {"submissions": 0}
    for path in sorted(glob.glob(os.path.join(g.ROOT, "data", "submissions", "*.json"))):
        sub = g.read_json(path)
        if not sub:
            continue
        rel = g.parse_dt(sub.get("release_date")) or g.parse_dt(sub.get("submitted_at"))
        if not rel:
            continue
        # Count submissions whose release falls in, or just before, this week.
        if not (start - timedelta(days=28) <= rel.astimezone(g.PACIFIC) <= end):
            continue
        key = norm_key(sub.get("track_title", ""), sub.get("artist", ""))
        if not key.strip("|"):
            continue
        meta["submissions"] += 1
        e = points.setdefault(key, {"points": 0.0, "title": sub.get("track_title", ""),
                                    "artist": sub.get("artist", ""),
                                    "label_or_independent": sub.get("label_or_independent", ""),
                                    "chart": sub.get("chart", "gospel")})
        e["points"] += 10.0
        if str(sub.get("radio_single", "")).strip().lower() in ("yes", "true", "y"):
            e["points"] += 5.0
    return points, meta


# ---------------------------------------------------------------------------
# INPUT 4 — the editorial desk (10%), and it may legitimately be zero
# ---------------------------------------------------------------------------
def load_editorial(start) -> tuple[dict, dict]:
    log = g.read_json(EDITORIAL_LOG, {"entries": []}) or {"entries": []}
    week = start.strftime("%Y-%m-%d")
    points, applied = {}, []
    for e in log.get("entries", []):
        if e.get("chart_week") != week:
            continue
        # Every adjustment REQUIRES a written reason. No reason, no effect.
        if not (e.get("reason") or "").strip():
            continue
        key = norm_key(e.get("title", ""), e.get("artist", ""))
        if not key.strip("|"):
            continue
        entry = points.setdefault(key, {"points": 0.0, "title": e.get("title", ""),
                                        "artist": e.get("artist", ""),
                                        "label_or_independent": e.get("label", ""),
                                        "chart": e.get("chart", "gospel")})
        entry["points"] += float(e.get("adjustment", 0) or 0)
        applied.append({"title": e.get("title"), "reason": e["reason"]})
    return points, {"adjustments": applied, "count": len(applied)}


# ---------------------------------------------------------------------------
# Weighting, with automatic redistribution
# ---------------------------------------------------------------------------
def active_weights(available: dict) -> tuple[dict, dict]:
    """
    Take the four published weights and spread the weight of any input that
    has NO data across the inputs that do. This is what lets the chart publish
    correctly with the editorial desk at zero, or with every streaming source
    switched off.
    """
    base = {"reporter_panel": 0.40, "streaming_momentum": 0.35,
            "release_activity": 0.15, "editorial": 0.10}
    live = {k: v for k, v in base.items() if available.get(k)}
    dropped = {k: v for k, v in base.items() if not available.get(k)}
    if not live:
        return {}, {"active": {}, "redistributed_from": list(dropped),
                    "note": "no input had any data"}
    total = sum(live.values())
    scaled = {k: v / total for k, v in live.items()}
    return scaled, {
        "active": {k: round(v, 4) for k, v in scaled.items()},
        "published_weights": base,
        "redistributed_from": sorted(dropped),
        "note": ("Weight of inputs with no data this week was redistributed "
                 "proportionally across the inputs that did have data."),
    }


def normalise(points: dict) -> dict:
    """Scale an input's raw points to 0–100 so inputs can be compared fairly."""
    if not points:
        return {}
    top = max(v["points"] for v in points.values()) or 1.0
    return {k: (v["points"] / top) * 100.0 for k, v in points.items()}


# ---------------------------------------------------------------------------
# Building one chart, and comparing it with history
# ---------------------------------------------------------------------------
def build_chart(scored: list, chart_key: str, size: int, prev_charts: dict,
                week_str: str, all_time: dict) -> list:
    entries = []
    prev = {e["key"]: e for e in (prev_charts.get(chart_key) or {}).get("entries", [])}

    for pos, (key, pts, info) in enumerate(scored[:size], start=1):
        seen = all_time.get(key, {})
        was = prev.get(key)
        last_week = was["current_position"] if was else None

        # Peak: the best position this title has EVER held, carried forward
        # from history. A re-entry resumes its prior peak — its past is not
        # erased just because it dropped off for a while.
        prior_peak = seen.get("peak_position")
        peak = min([p for p in (prior_peak, pos) if p is not None])

        weeks = seen.get("weeks_on_chart", 0) + 1
        first_charted = seen.get("first_charted_date") or week_str
        debut = first_charted == week_str and weeks == 1
        re_entry = bool(seen and not was and not debut)
        bullet = bool(last_week and pos < last_week) or debut

        entries.append({
            "key": key,
            "title": info["title"],
            "artist": info["artist"],
            "label_or_independent": info.get("label_or_independent", ""),
            "current_position": pos,
            "last_week": last_week,
            "peak_position": peak,
            "weeks_on_chart": weeks,
            "first_charted_date": first_charted,
            "debut": debut,
            "re_entry": re_entry,
            "bullet": bullet,
            "points": round(pts, 3),
        })
    return entries


def apply_falloff(entries: list, recurrents: list, chart_key: str) -> list:
    """
    A title leaves after 20 weeks unless it is still in the top 10. Long
    runners move to Recurrents so a record everybody already knows stops
    blocking a new one from charting.
    """
    kept = []
    for e in entries:
        if e["weeks_on_chart"] > FALLOFF_WEEKS and e["current_position"] > FALLOFF_PROTECT_TOP:
            r = dict(e)
            r["moved_to_recurrents"] = True
            r["from_chart"] = chart_key
            recurrents.append(r)
        else:
            kept.append(e)
    for i, e in enumerate(kept, start=1):   # close the gaps
        e["current_position"] = i
        e["peak_position"] = min(e["peak_position"], i)
    return kept


# ---------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true",
                    help="publish even if this week already published")
    args = ap.parse_args()

    start, end = tracking_week()
    week_str = start.strftime("%Y-%m-%d")
    print("GNA chart run")
    print("  tracking week: %s 12:00 AM  ->  %s 11:59 PM Pacific"
          % (start.strftime("%a %b %-d"), end.strftime("%a %b %-d")))

    # --- load history FIRST. It is never regenerated, only added to. --------
    history = g.read_json(HISTORY, None)
    if history is None:
        history = {
            "_README": [
                "THE PERMANENT MEMORY OF THE GNA CHARTS.",
                "",
                "This file is never regenerated from scratch and never deleted.",
                "'weeks_on_chart' and 'peak_position' are only true because this",
                "file carries forward from one week to the next.",
                "",
                "If you delete this file, every chart history on the site becomes",
                "fiction. Back it up; never 'clean' it.",
            ],
            "created": g.iso(g.now_utc()),
            "last_published": None,
            "charts": {},
            "recurrents": [],
            "all_time": {},
            "runs": [],
        }
        print("  history.json did not exist — initialising it for the first time")
    else:
        print("  history loaded: %d past runs, %d titles known"
              % (len(history.get("runs", [])), len(history.get("all_time", {}))))

    if history.get("last_published") == week_str and not args.force:
        print("  week %s already published. Nothing to do. (--force overrides)" % week_str)
        return 0

    # --- gather the four inputs -------------------------------------------
    panel, panel_meta = load_reporter_spins(start, end)
    stream, stream_meta = load_streaming_momentum()
    release, release_meta = load_release_activity(start, end)
    editorial, editorial_meta = load_editorial(start)

    print("  input 1 reporter panel  : %d titles from %d reports"
          % (len(panel), panel_meta["reports"]))
    print("  input 2 streaming       : %d titles (%d sources enabled, %d off)"
          % (len(stream), len(stream_meta["enabled_sources"]),
             len(stream_meta["disabled_sources"])))
    print("  input 3 release activity: %d titles from %d submissions"
          % (len(release), release_meta["submissions"]))
    print("  input 4 editorial desk  : %d adjustments" % editorial_meta["count"])

    available = {"reporter_panel": bool(panel), "streaming_momentum": bool(stream),
                 "release_activity": bool(release), "editorial": bool(editorial)}
    weights, weight_meta = active_weights(available)
    if weights:
        print("  active weights: %s" % ", ".join(
            "%s %.0f%%" % (k.replace("_", " "), v * 100) for k, v in sorted(weights.items())))
    if weight_meta.get("redistributed_from"):
        print("  redistributed the weight of: %s"
              % ", ".join(weight_meta["redistributed_from"]))

    # --- combine ----------------------------------------------------------
    inputs = {"reporter_panel": panel, "streaming_momentum": stream,
              "release_activity": release, "editorial": editorial}
    normalised = {k: normalise(v) for k, v in inputs.items()}

    info_by_key: dict = {}
    for src in inputs.values():
        for key, v in src.items():
            slot = info_by_key.setdefault(key, {})
            for f in ("title", "artist", "label_or_independent", "chart"):
                if v.get(f) and not slot.get(f):
                    slot[f] = v[f]

    totals: dict = {}
    for name, weight in weights.items():
        for key, score in normalised.get(name, {}).items():
            totals[key] = totals.get(key, 0.0) + score * weight

    if not totals:
        # THE HONEST OUTCOME. There is no measured activity, so there is no
        # chart. We record the run and publish nothing rather than inventing
        # twenty titles to fill the page.
        print("\n  No measured activity for this week.")
        print("  Publishing NO chart rather than inventing one.")
        history.setdefault("runs", []).append({
            "chart_week": week_str, "ran_at": g.iso(g.now_utc()),
            "published": False,
            "reason": "no measured input data for this tracking week",
            "inputs": {"panel": panel_meta, "streaming": stream_meta,
                       "release": release_meta, "editorial": editorial_meta},
        })
        if not args.dry_run:
            g.write_json(HISTORY, history)
            import render_site
            render_site.render_all()
        return 0

    # --- rank into the four charts ----------------------------------------
    prev_charts = history.get("charts", {})
    all_time = history.get("all_time", {})
    recurrents: list = []

    def scored_for(pred):
        rows = [(k, p, info_by_key.get(k, {})) for k, p in totals.items()
                if pred(info_by_key.get(k, {}).get("chart", "gospel"))]
        rows.sort(key=lambda r: (-r[1], r[2].get("title", "")))
        return rows

    new_charts = {}
    for chart_key, pred in [
        ("gospel_20", lambda c: c == "gospel"),
        ("christian_20", lambda c: c == "christian"),
        ("albums_20", lambda c: c == "album"),
    ]:
        entries = build_chart(scored_for(pred), chart_key, CHART_SIZES[chart_key],
                              prev_charts, week_str, all_time)
        entries = apply_falloff(entries, recurrents, chart_key)
        new_charts[chart_key] = {"name": chart_key, "entries": entries}

    # --- What's Hot: fastest movers only, never reputation ----------------
    movers = []
    for ck in ("gospel_20", "christian_20"):
        for e in new_charts[ck]["entries"]:
            if e["debut"]:
                gain = 25.0                       # a debut is movement
            elif e["last_week"]:
                gain = float(e["last_week"] - e["current_position"])
            else:
                gain = 0.0
            if gain > 0:
                movers.append((gain, e))
    movers.sort(key=lambda m: (-m[0], m[1]["current_position"]))
    hot = []
    for pos, (gain, e) in enumerate(movers[:CHART_SIZES["whats_hot"]], start=1):
        h = dict(e)
        h["current_position"] = pos
        h["movement_gain"] = gain
        hot.append(h)
    new_charts["whats_hot"] = {"name": "whats_hot", "entries": hot}

    # --- update the permanent memory --------------------------------------
    for chart_key, chart in new_charts.items():
        if chart_key == "whats_hot":
            continue
        for e in chart["entries"]:
            rec = all_time.setdefault(e["key"], {})
            rec["title"] = e["title"]
            rec["artist"] = e["artist"]
            rec["weeks_on_chart"] = e["weeks_on_chart"]
            rec["peak_position"] = min(
                [p for p in (rec.get("peak_position"), e["peak_position"]) if p is not None])
            rec["first_charted_date"] = e["first_charted_date"]
            rec["last_seen_week"] = week_str

    history["charts"] = new_charts
    history["all_time"] = all_time
    history["recurrents"] = (history.get("recurrents") or []) + recurrents
    history["last_published"] = week_str
    history.setdefault("runs", []).append({
        "chart_week": week_str,
        "ran_at": g.iso(g.now_utc()),
        "published": True,
        "weights": weight_meta,
        "counts": {k: len(v["entries"]) for k, v in new_charts.items()},
        "inputs": {"panel": panel_meta, "streaming": stream_meta,
                   "release": release_meta, "editorial": editorial_meta},
    })

    for k, v in new_charts.items():
        print("  %-14s %d entries" % (k, len(v["entries"])))
    if recurrents:
        print("  %d title(s) moved to Recurrents" % len(recurrents))

    if args.dry_run:
        print("\n  --dry-run: history NOT written")
        return 0

    # Back up the previous history before replacing it. Cheap insurance on
    # the one file whose loss cannot be undone.
    full = os.path.join(g.ROOT, HISTORY)
    if os.path.exists(full):
        shutil.copyfile(full, full + ".bak")

    g.write_json(HISTORY, history)
    conf = g.read_json("data/site-config.json", {}) or {}
    if conf.get("charts", {}).get("first_publication_date") is None:
        conf.setdefault("charts", {})["first_publication_date"] = week_str
        g.write_json("data/site-config.json", conf)

    import render_site
    render_site.render_all()
    print("\n  Published chart week %s and rebuilt the pages." % week_str)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception:
        # FAIL LOUDLY. Never write a partial or empty history — last week's
        # file stays exactly as it was, and the run is visibly red.
        traceback.print_exc()
        print("\nFATAL: chart run failed. history.json was NOT modified.",
              file=sys.stderr)
        raise SystemExit(1)
