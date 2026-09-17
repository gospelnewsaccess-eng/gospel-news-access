#!/usr/bin/env python3
"""
wire.py — the news engine. This is what keeps Gospel News Access alive.

Plain English: every 30 minutes GitHub runs this script. It reads every
verified feed, pulls a photo for each story, decides what is breaking and what
is not, saves everything to data/articles.json, and then rebuilds the website's
HTML pages. Then it commits the result. Nobody has to be awake for any of it.

If this script stops running, the site stops being a news wire and becomes a
brochure. Everything else in the repository is in service of this file.

WHAT IT WILL NOT DO
  - It will not use a feed that has not passed scripts/verify_feeds.py.
  - It will not download, re-host, crop or watermark another outlet's photo.
    It hotlinks the publisher's image, names the publisher under it, and links
    the headline to the publisher's own page. That is the Google News model.
  - It will not invent anything. No story, headline, summary, byline, outlet
    or timestamp is ever synthesised. Every field comes from the feed.
  - It will not leave a stale BREAKING flag up. See the kill switch below.

Usage:  python3 scripts/wire.py [--force-all] [--no-render] [--dry-run]
"""

from __future__ import annotations

import argparse
import sys
from datetime import timedelta

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import gnalib as g  # noqa: E402

# --- The editorial rules, all in one place so they are easy to audit --------
BREAKING_WINDOW_MIN = 90      # a Tier 1 story this fresh counts as breaking
BREAKING_TTL_HOURS = 12       # ...and the flag dies this long after we saw it
HERO_MAX_AGE_HOURS = 72       # nothing older may ever hold the lead slot
RETENTION_DAYS = 21           # how long a story stays in the store
MAX_STORED = 600              # hard ceiling so the data file cannot balloon
OG_FETCH_BUDGET = 30          # article pages fetched per run for og:image
FEED_TIMEOUT = 20


# ---------------------------------------------------------------------------
# Deciding which feeds are due this run
# ---------------------------------------------------------------------------
def is_due(src: dict, state: dict, force: bool) -> bool:
    """Tier 1 every 30 min; tiers 2 and 3 hourly. Cheap and predictable."""
    if force:
        return True
    last = g.parse_dt(state.get("last_polled", {}).get(src["name"]))
    if not last:
        return True
    interval = 30 if src.get("tier") == 1 else 60
    return g.age_minutes(last) >= (interval - 2)  # -2 so cron jitter cannot skip


# ---------------------------------------------------------------------------
# Feed health: catch the quiet death of a source
# ---------------------------------------------------------------------------
def record_health(health: dict, name: str, ok: bool, detail: str, count: int) -> None:
    entry = health.setdefault(
        name, {"consecutive_zero": 0, "consecutive_error": 0, "flagged": False}
    )
    entry["last_checked"] = g.iso(g.now_utc())
    entry["last_item_count"] = count
    if ok and count > 0:
        entry["consecutive_zero"] = 0
        entry["consecutive_error"] = 0
        entry["flagged"] = False
        entry["last_status"] = "ok"
        entry.pop("last_error", None)
    else:
        if ok:
            entry["consecutive_zero"] += 1
            entry["last_status"] = "zero items"
        else:
            entry["consecutive_error"] += 1
            entry["last_status"] = "error"
            entry["last_error"] = detail
        # The brief's rule: zero items twice in a row is a logged problem.
        if entry["consecutive_zero"] >= 2 or entry["consecutive_error"] >= 2:
            entry["flagged"] = True
            entry["flagged_since"] = entry.get("flagged_since") or g.iso(g.now_utc())


# ---------------------------------------------------------------------------
# Turning one feed entry into one stored story
# ---------------------------------------------------------------------------
def build_story(entry: dict, src: dict, seen_at, og_budget: list) -> dict | None:
    link = (entry.get("link") or "").strip()
    title = (entry.get("title") or "").strip()
    if not link or not title:
        return None

    published = g.parse_dt(entry.get("published_raw"))
    if not published:
        # No date means we cannot reason about freshness, breaking status or
        # the 72-hour hero rule. We do not guess a timestamp. We drop it.
        return None
    if published > g.now_utc() + timedelta(hours=6):
        return None  # a feed with a broken clock

    # Google News wraps the outlet name into the headline and names the real
    # publisher in a <source> element. Use the real publisher.
    outlet = src["name"]
    if src.get("tier") == 1:
        clean, suffix = g.clean_google_title(title)
        title = clean or title
        outlet = entry.get("origin_name") or suffix or "Google News"
    outlet_url = entry.get("origin_url") or ""

    # --- the photo chain. og:image costs a page fetch, so it is budgeted. ---
    allow_page = og_budget[0] > 0
    image = g.extract_image(entry, allow_page_fetch=allow_page)
    if image and image["via"] == "og:image":
        og_budget[0] -= 1

    summary = g.strip_html(
        entry.get("summary_html") or entry.get("content_html") or "", 260
    )
    # Google News descriptions are just a list of links to other outlets.
    if src.get("tier") == 1 and summary.count("http") > 1:
        summary = ""

    return {
        "id": g.story_id(link),
        "title": title,
        "link": link,
        "summary": summary,
        "outlet": outlet,
        "outlet_url": outlet_url,
        "source_feed": src["name"],
        "tier": src.get("tier", 3),
        "category": src.get("category", "faith"),
        "published": g.iso(published),
        "first_seen": g.iso(seen_at),
        "image": image,          # None is a valid, designed outcome
        "breaking": False,
        "breaking_expires_at": None,
    }


def apply_breaking(story: dict) -> None:
    """
    BREAKING, with the kill switch built in.

    A Tier 1 story seen within 90 minutes of publication is flagged breaking,
    and in the same breath we write down when that flag must die — 12 hours
    later. The renderer checks that expiry on every single page build, so the
    flag removes itself even if this script never runs again.

    A stale BREAKING banner is the single worst failure this site could have,
    so it is designed out rather than watched for.
    """
    if story["tier"] != 1:
        return
    published = g.parse_dt(story["published"])
    seen = g.parse_dt(story["first_seen"])
    if not published or not seen:
        return
    if 0 <= (seen - published).total_seconds() / 60.0 <= BREAKING_WINDOW_MIN:
        story["breaking"] = True
        story["breaking_expires_at"] = g.iso(seen + timedelta(hours=BREAKING_TTL_HOURS))


# ---------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force-all", action="store_true",
                    help="poll every verified feed regardless of schedule")
    ap.add_argument("--no-render", action="store_true",
                    help="update data only, do not rebuild HTML")
    ap.add_argument("--dry-run", action="store_true",
                    help="fetch and report, write nothing")
    args = ap.parse_args()

    run_at = g.now_utc()
    doc = g.read_json("data/news-sources.json")
    if not doc:
        print("FATAL: data/news-sources.json missing", file=sys.stderr)
        return 1

    all_sources = doc.get("sources", [])
    verified = [s for s in all_sources if s.get("status") == "verified"]
    unverified = len(all_sources) - len(verified)

    print("Wire run %s" % g.iso(run_at))
    print("  %d sources on file, %d verified, %d skipped as unverified"
          % (len(all_sources), len(verified), unverified))

    if not verified:
        # This is not a crash — it is the safety rule working. But it must be
        # loud, because it means the site has no legal source of stories.
        print("\n  NO VERIFIED FEEDS. The wire refuses to publish from an\n"
              "  unverified source. Run scripts/verify_feeds.py first\n"
              "  (workflow: .github/workflows/verify-feeds.yml).", file=sys.stderr)
        return 2

    store = g.read_json("data/articles.json", {"items": []}) or {"items": []}
    existing = {s["id"]: s for s in store.get("items", [])}
    state = g.read_json("data/wire-state.json", {"last_polled": {}}) or {"last_polled": {}}
    state.setdefault("last_polled", {})
    health = g.read_json("data/feed-health.json", {"feeds": {}}) or {"feeds": {}}
    health.setdefault("feeds", {})

    og_budget = [OG_FETCH_BUDGET]
    polled = added = updated = 0
    seen_titles = {g.title_key(s["title"]): s["id"] for s in existing.values()}

    for src in verified:
        if not is_due(src, state, args.force_all):
            continue
        polled += 1
        raw, meta = g.fetch(src["url"], timeout=FEED_TIMEOUT)
        if raw is None:
            record_health(health["feeds"], src["name"], False, str(meta), 0)
            print("  !! %-44s %s" % (src["name"][:44], meta))
            continue

        entries, err = g.parse_feed(raw)
        if err:
            record_health(health["feeds"], src["name"], False, err, 0)
            print("  !! %-44s %s" % (src["name"][:44], err[:48]))
            continue

        record_health(health["feeds"], src["name"], True, "", len(entries))
        state["last_polled"][src["name"]] = g.iso(run_at)

        new_here = 0
        for entry in entries[:25]:
            story = build_story(entry, src, run_at, og_budget)
            if not story:
                continue

            if story["id"] in existing:
                # Known story. Backfill a photo if we have found one since.
                prev = existing[story["id"]]
                if not prev.get("image") and story.get("image"):
                    prev["image"] = story["image"]
                    updated += 1
                continue

            # Same story arriving from a different query or outlet.
            tkey = g.title_key(story["title"])
            if tkey and tkey in seen_titles:
                twin = existing.get(seen_titles[tkey])
                if twin and not twin.get("image") and story.get("image"):
                    twin["image"] = story["image"]
                    updated += 1
                continue

            apply_breaking(story)
            existing[story["id"]] = story
            if tkey:
                seen_titles[tkey] = story["id"]
            added += 1
            new_here += 1

        if new_here:
            print("  +%-3d %-44s (%d in feed)" % (new_here, src["name"][:44], len(entries)))

    # --- prune: age out old stories, then cap the total ---------------------
    cutoff = run_at - timedelta(days=RETENTION_DAYS)
    items = [
        s for s in existing.values()
        if (g.parse_dt(s["published"]) or run_at) >= cutoff
    ]
    items.sort(key=lambda s: s["published"], reverse=True)
    dropped = len(existing) - len(items)
    items = items[:MAX_STORED]

    live_breaking = sum(
        1 for s in items
        if s.get("breaking")
        and s.get("breaking_expires_at")
        and (g.parse_dt(s["breaking_expires_at"]) or run_at) > run_at
    )
    with_photo = sum(1 for s in items if s.get("image"))

    print("\n  %d feeds polled | %d new | %d photos backfilled | %d aged out"
          % (polled, added, updated, dropped))
    print("  %d stories stored | %d with a photo (%d%%) | %d live breaking"
          % (len(items), with_photo,
             round(100 * with_photo / len(items)) if items else 0, live_breaking))

    flagged = [n for n, h in health["feeds"].items() if h.get("flagged")]
    if flagged:
        print("  %d feed(s) flagged in data/feed-health.json: %s"
              % (len(flagged), ", ".join(sorted(flagged)[:4])))

    if args.dry_run:
        print("\n  --dry-run: nothing written")
        return 0

    store = {
        "generated_at": g.iso(run_at),
        "story_count": len(items),
        "with_photo": with_photo,
        "items": items,
    }
    g.write_json("data/articles.json", store)
    g.write_json("data/wire-state.json", state)
    health["updated_at"] = g.iso(run_at)
    health["flagged_feeds"] = sorted(flagged)
    g.write_json("data/feed-health.json", health)

    if not args.no_render:
        import render_site
        render_site.render_all()
        print("  pages rebuilt")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
