# Learning log — Gospel News Access

Short lessons, one per new idea, so nothing lives only in a chat window.

## Oct 29, 2026 — The robot that showed up late

**What broke:** the weekly charts stopped after Oct 13. Oct 20 and Oct 27 were skipped.

**Why:** GitHub's scheduled jobs are like a bus that often runs two to four hours late. The charts robot checked "is it exactly 12 noon?" when it arrived. It arrived at 3pm, saw the wrong hour, and went home without publishing.

**The fix:** the robot now accepts any arrival from Tuesday noon through Wednesday, with a Wednesday backup run. A separate safety lock (the engine refuses to publish the same week twice) means the extra chances can never double-publish.

**The lesson:** never build an automatic job that needs to start at an exact minute. Give it a window, and a lock so it only acts once.

## Nov 22, 2026 — One light switch for ads
Google ads need one small line of code in the hidden top section of every page (the "head"), plus a file called ads.txt that proves to advertisers we really sell space through Google. Instead of pasting that line into every page by hand, there is one switch: ADSENSE_PUB at the top of scripts/layout.py. Fill it in and run tools/adsense.py, and every page gets the line between two marker comments; empty it and run again, and it all comes back out. The markers work like labels on a fuse box: the tool always knows which wire is its own. Press releases and the charity (CDC) pages stay ad-free on purpose.
