#!/usr/bin/env python3
"""
video.py — builds the video wall.

Plain English: reads the list of YouTube channels in data/video-sources.json,
fetches each channel's public feed, and records the newest videos. The video
page then embeds the creator's own YouTube player.

The channel list is EMPTY right now, on purpose — no channel ID has been
supplied yet. That is not a bug and the page handles it: video.html renders a
clear "no channels connected" notice instead of a broken grid. Add a channel ID
and videos appear by themselves within six hours.

WHAT IT WILL NOT DO
  Never re-hosts, downloads, re-uploads or watermarks anyone's footage. The
  video plays from the original creator's own player, on their channel, and
  their view count is theirs.

Usage:  python3 scripts/video.py [--no-render]
"""

from __future__ import annotations

import argparse
import sys

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import gnalib as g  # noqa: E402

FEED = "https://www.youtube.com/feeds/videos.xml?channel_id=%s"
MAX_PER_CHANNEL = 12
MAX_TOTAL = 48


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-render", action="store_true")
    args = ap.parse_args()

    conf = g.read_json("data/video-sources.json", {}) or {}
    channels = [c for c in conf.get("channels", []) if c.get("channel_id")]

    print("Video run %s" % g.iso(g.now_utc()))
    if not channels:
        print("  No channels configured — this is the expected state until a")
        print("  channel ID is added to data/video-sources.json.")
        print("  Writing an empty video list; video.html renders correctly with zero videos.")
        g.write_json("data/videos.json", {
            "_README": ["Written by scripts/video.py. Do not edit by hand."],
            "generated_at": g.iso(g.now_utc()),
            "note": "No channels configured yet. Add one to data/video-sources.json.",
            "items": [],
        })
        if not args.no_render:
            import render_site
            render_site.render_all()
        return 0

    items = []
    for ch in channels:
        cid = ch["channel_id"].strip()
        if not cid.startswith("UC") or len(cid) != 24:
            print("  !! %s: '%s' does not look like a YouTube channel ID "
                  "(should start UC and be 24 characters). Skipped." % (ch.get("name", "?"), cid))
            continue
        raw, meta = g.fetch(FEED % cid, timeout=20)
        if raw is None:
            print("  !! %-30s %s" % (ch.get("name", cid)[:30], meta))
            continue
        entries, err = g.parse_feed(raw)
        if err:
            print("  !! %-30s %s" % (ch.get("name", cid)[:30], err[:50]))
            continue

        count = 0
        for e in entries[:MAX_PER_CHANNEL]:
            link = e.get("link", "")
            vid = ""
            if "watch?v=" in link:
                vid = link.split("watch?v=", 1)[1].split("&")[0]
            if not vid:
                continue
            published = g.parse_dt(e.get("published_raw"))
            if not published:
                continue
            img = g.extract_image(e, allow_page_fetch=False)
            items.append({
                "video_id": vid,
                "title": e.get("title", ""),
                "link": link,
                "channel": ch.get("name", ""),
                "channel_id": cid,
                "published": g.iso(published),
                "summary": g.strip_html(e.get("summary_html", ""), 200),
                "thumbnail": (img or {}).get("url"),
            })
            count += 1
        print("  +%-3d %s" % (count, ch.get("name", cid)))

    items.sort(key=lambda v: v["published"], reverse=True)
    items = items[:MAX_TOTAL]
    print("  %d videos stored" % len(items))

    g.write_json("data/videos.json", {
        "_README": ["Written by scripts/video.py. Do not edit by hand."],
        "generated_at": g.iso(g.now_utc()),
        "count": len(items),
        "items": items,
    })
    if not args.no_render:
        import render_site
        render_site.render_all()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
