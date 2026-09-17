#!/usr/bin/env python3
"""
verify_feeds.py — prove every feed URL is real before the wire is allowed to
use it.

Plain English: a news wire's worst quiet failure is a feed that died months
ago. Nothing crashes. The page just gets thinner and thinner and nobody
notices. This script exists to make that impossible.

For every source in data/news-sources.json it:
  1. fetches the URL,
  2. confirms the response is valid XML with real items,
  3. confirms at least one item is dated within the last 30 days,
  4. writes the date it checked into the file.

If the main URL fails it tries each alternate in "url_candidates" and promotes
whichever one actually works.

THE IMPORTANT PART: scripts/wire.py ignores any source that is not marked
"verified". So a URL that has never passed this check, or that has stopped
working, cannot put a story on the live site.

Run it on GitHub Actions (.github/workflows/verify-feeds.yml), which has open
internet access.

Usage:  python3 scripts/verify_feeds.py [--only-unverified] [--tier N]
"""

from __future__ import annotations

import argparse
import sys
from datetime import timedelta

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import gnalib as g  # noqa: E402

FRESH_DAYS = 30


def check_url(url: str) -> dict:
    """Fetch one URL and report exactly what came back."""
    raw, meta = g.fetch(url, timeout=25)
    if raw is None:
        return {"ok": False, "error": str(meta)}

    entries, err = g.parse_feed(raw)
    if err:
        return {"ok": False, "error": err}
    if not entries:
        return {"ok": False, "error": "feed parsed but contained zero items"}

    newest = None
    dated = 0
    for e in entries:
        dt = g.parse_dt(e.get("published_raw"))
        if dt:
            dated += 1
            if newest is None or dt > newest:
                newest = dt

    if newest is None:
        return {
            "ok": False,
            "error": "feed has %d items but none carry a readable date" % len(entries),
        }

    cutoff = g.now_utc() - timedelta(days=FRESH_DAYS)
    if newest < cutoff:
        return {
            "ok": False,
            "error": "stale: newest item is %s, older than %d days"
            % (g.iso(newest), FRESH_DAYS),
            "newest": g.iso(newest),
        }

    # How many of these items would actually arrive with a photo? Useful to
    # know, never a reason to reject a feed.
    with_image = sum(
        1 for e in entries[:12] if g.extract_image(e, allow_page_fetch=False)
    )

    return {
        "ok": True,
        "count": len(entries),
        "dated": dated,
        "newest": g.iso(newest),
        "with_image": with_image,
        "sampled": min(12, len(entries)),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only-unverified", action="store_true",
                    help="skip sources already marked verified")
    ap.add_argument("--tier", type=int, default=0, help="check one tier only")
    args = ap.parse_args()

    doc = g.read_json("data/news-sources.json")
    if not doc:
        print("FATAL: data/news-sources.json is missing", file=sys.stderr)
        return 1

    sources = doc.get("sources", [])
    today = g.now_utc().strftime("%Y-%m-%d")
    passed = failed = skipped = 0

    print("Verifying %d feeds (freshness window: %d days)\n" % (len(sources), FRESH_DAYS))

    for src in sources:
        if args.tier and src.get("tier") != args.tier:
            continue
        if args.only_unverified and src.get("status") == "verified":
            skipped += 1
            continue

        # Try the primary URL, then every alternate, and keep the winner.
        candidates = [src["url"]] + [
            u for u in src.get("url_candidates", []) if u != src["url"]
        ]
        result = None
        winner = None
        for url in candidates:
            result = check_url(url)
            if result["ok"]:
                winner = url
                break

        if result and result["ok"]:
            if winner != src["url"]:
                print("  ~ PROMOTED alternate URL for %s" % src["name"])
                src["url"] = winner
            src["status"] = "verified"
            src["verified"] = today
            src["verified_item_count"] = result["count"]
            src["verified_newest_item"] = result["newest"]
            src["last_error"] = None
            passed += 1
            print("  OK   [t%d] %-42s %3d items, newest %s, %d/%d with photo"
                  % (src["tier"], src["name"][:42], result["count"],
                     result["newest"][:10], result["with_image"], result["sampled"]))
        else:
            src["status"] = "failed"
            src["verified"] = None
            src["last_error"] = (result or {}).get("error", "unknown")
            src["last_checked"] = today
            failed += 1
            print("  FAIL [t%d] %-42s %s"
                  % (src["tier"], src["name"][:42], src["last_error"][:70]))

    doc["last_verification_run"] = g.iso(g.now_utc())
    doc["verification_summary"] = {
        "verified": passed, "failed": failed, "skipped": skipped,
    }
    g.write_json("data/news-sources.json", doc)

    print("\n%d verified, %d failed, %d skipped" % (passed, failed, skipped))
    print("Only the %d verified sources will be read by the wire." % passed)

    if passed == 0:
        print("\nFATAL: not one feed verified. Refusing to report success.",
              file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
