# Going live — the order things must happen in

Follow these in order. Step 1 is not optional and nothing else works until it
is done.

---

## Step 1 — Give the build access to write to the repository

**This is currently blocking everything.** The whole site is built and tested,
but it could not be committed, because the Claude GitHub App on the
`gospelnewsaccess-eng` organisation has **read-only** access. Every attempt to
write was refused with `403 Resource not accessible by integration`.

Somebody who is an **owner of the `gospelnewsaccess-eng` GitHub organisation**
needs to do one of these:

- Install or re-install the app with write access:
  **https://github.com/apps/claude/installations/select_target**
  Choose the `gospelnewsaccess-eng` organisation, make sure
  `gospel-news-access` is selected, and grant **Read and write** access to
  repository contents and workflows.
- Or reconnect GitHub from claude.ai:
  **https://claude.ai/customize/connectors?auth_start=github&auth_start_force=1**

Once that is done the finished site can be pushed in a single commit.

---

## Step 2 — Turn on GitHub Pages

1. Go to the repository → **Settings** → **Pages**.
2. Under **Build and deployment**, set **Source** to **Deploy from a branch**.
3. Set the branch to **main** and the folder to **/ (root)**.
4. Click **Save**.

After a minute or two the site is live at:

```
https://gospelnewsaccess-eng.github.io/gospel-news-access/
```

---

## Step 3 — Verify the feeds (do this BEFORE the first wire run)

The wire refuses to publish from a source it has not verified. Nothing will
appear on the site until this has run once.

1. Repository → **Actions** tab.
2. Choose **Verify feeds** in the left list.
3. Click **Run workflow** → **Run workflow**.
4. Wait about 3–5 minutes.

Open the run and read the log. Every feed reports as `OK` or `FAIL` with the
reason. Feeds that fail are simply switched off — they cannot put a story on
the site. Failures are normal; publishers change their feed addresses.

> If a feed you want fails, add the correct address to its `url_candidates`
> list in `data/news-sources.json` and run the workflow again.

---

## Step 4 — Run the wire for the first time

1. **Actions** → **News wire** → **Run workflow**.
2. Wait 2–4 minutes.

The log tells you how many stories arrived and how many carried a photo. The
front page will be full when it finishes.

After this it runs itself every 30 minutes. You never need to touch it again.

---

## Step 5 — Check it worked

Open the live address and confirm:

- [ ] Headlines are real and recent
- [ ] Photographs are showing on the story cards
- [ ] Clicking a headline goes to the publication that wrote it
- [ ] Timestamps look sensible ("14 min ago", "3 hrs ago")
- [ ] The page does not scroll sideways on your phone

---

## Step 6 — The things only you can supply

These are marked `null` in `data/site-config.json` and currently render as
**nothing at all** on the live site. That is deliberate — an invented phone
number or a programme that does not exist could send somebody in real trouble
to a door that does not open.

| What is needed | Where it goes | What it unblocks |
|---|---|---|
| A monitored email address | `organization.email_general` | The contact page, Google News application |
| Ownership statement | `organization.ownership_disclosure` | Search credibility (E-E-A-T) |
| Your YouTube channel ID | `data/video-sources.json` | The whole video wall |
| CDC address, phone, programmes | `cdc.*` | The CDC pages |
| A form service endpoint | `forms.*` | Every form on the site |
| A logo, 512×512 and rectangular | (image files) | Google News application |

See `runbook/forms-setup.md` for the forms and `runbook/search-setup.md` for
Google, Google News and Bing.

---

## Step 7 — Start the charts

The charts cannot publish until there is something to measure. Two things start
the clock:

1. **Recruit reporters.** Radio stations, syndicated shows, streaming
   programmers and DJs who will report weekly spin counts. Add each confirmed
   one to `data/reporters.json`. This is 40% of a chart position and is the
   single most valuable thing to work on.
2. **Open submissions.** Switch on the form on `submit-music.html`.

There is also a decision waiting on the streaming input (35%): all three
streaming sources are switched **off** in `data/chart-sources.json` because
their developer terms have not been read. Until at least one is reviewed and
enabled, that 35% is redistributed across the other inputs. The chart still
publishes correctly — it is simply measuring radio and releases only, and the
methodology page says so.

Until any of this exists, `charts.html` shows an honest "no chart has published
yet" notice. It does not show an invented chart.
