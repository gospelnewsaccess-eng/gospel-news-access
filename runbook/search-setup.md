# Getting Gospel News Access into Google, Google News and Bing

Written for somebody who has never used any of these tools. Follow it in order.
Nothing here is dangerous and nothing costs money.

You will need to be signed in to a Google account. Use a real working account
you will still have in two years — **not** a throwaway.

**Time needed:** about 40 minutes, then a wait of a few days for Google.

---

## Before you start: what your site address is

```
https://gospelnewsaccess-eng.github.io/gospel-news-access/
```

Copy that exactly. The trailing slash matters in some boxes.

Two files that already exist and that these tools will ask about:

| File | Address | What it is |
|---|---|---|
| Sitemap | `https://gospelnewsaccess-eng.github.io/gospel-news-access/sitemap.xml` | A list of every page on the site |
| News sitemap | `https://gospelnewsaccess-eng.github.io/gospel-news-access/sitemap-news.xml` | Only our own reporting from the last 48 hours |

---

# PART 1 — Google Search Console

This is how you tell Google the site exists, and how you see what people search
to find you.

### Step 1 — open it
Go to **https://search.google.com/search-console** and sign in.

### Step 2 — add the property
1. If this is your first time, you will see a welcome screen. Otherwise click
   the dropdown at the top left and choose **Add property**.
2. You will be offered two boxes: **Domain** and **URL prefix**.
3. Use the **URL prefix** box on the right. (The Domain box needs you to own a
   domain name and change its DNS settings. We are on a github.io address, so
   that option will not work.)
4. Paste: `https://gospelnewsaccess-eng.github.io/gospel-news-access/`
5. Click **Continue**.

### Step 3 — prove the site is yours
Google offers several methods. **Use the HTML file method.**

1. Choose **HTML file** — "Upload an HTML file to your site".
2. Click the link to download the file. It will be named something like
   `google1a2b3c4d5e6f.html`.
3. That file must go into the top level of the repository. Either:
   - Ask your developer to add it and commit it to `main`, **or**
   - Do it yourself on GitHub: open
     `https://github.com/gospelnewsaccess-eng/gospel-news-access`,
     click **Add file → Upload files**, drag the downloaded file in, then click
     **Commit changes**.
4. Wait about two minutes for the site to rebuild.
5. Check it worked by opening the file's address in your browser:
   `https://gospelnewsaccess-eng.github.io/gospel-news-access/google1a2b3c4d5e6f.html`
   (use your real file name). You should see a line of text, not an error.
6. Back in Search Console, click **Verify**.

> **If verification fails:** wait five minutes and press Verify again. GitHub
> Pages can take a moment to publish. Do not delete the file afterwards —
> Google re-checks it periodically and will un-verify you if it disappears.

### Step 4 — submit the sitemap
1. In the left menu click **Sitemaps**.
2. In the box marked "Add a new sitemap" type just: `sitemap.xml`
3. Click **Submit**.
4. Repeat with: `sitemap-news.xml`

Status will say "Couldn't fetch" for a few hours at first. That is normal.
Check again the next day; it should say **Success**.

### Step 5 — ask Google to look at the front page now
1. At the very top of the page there is a search box that says
   "Inspect any URL in...". Paste your site address into it and press Enter.
2. Wait for it to finish, then click **Request indexing**.

This only speeds up the front page. The rest gets found through the sitemap.

### What to expect
Nothing for 3–7 days. Then pages start appearing. Do not resubmit repeatedly —
it does not help.

---

# PART 2 — Google News Publisher Center

This is what puts the site in the **News** tab and in Google News itself.

> **Be realistic about this one.** Google requires a publication to show a track
> record of its own original reporting. A site that is only a wire of other
> people's headlines will usually be rejected. Apply once there are a genuine
> handful of original stories published under our own byline. Applying too
> early and being rejected is worse than waiting.

### Step 1 — open it
Go to **https://publishercenter.google.com** and sign in with the same Google
account you used for Search Console.

### Step 2 — create the publication
1. Click **Add publication**.
2. **Publication name:** `Gospel News Access`
3. **Publication website:** `https://gospelnewsaccess-eng.github.io/gospel-news-access/`
4. Click **Add**.

### Step 3 — fill in the publication details
In **Publication settings**, you will be asked for:

- **Primary language:** English
- **Primary country:** United States (or wherever the newsroom actually is)
- **Category:** News
- **Contact email** — this must be a real monitored inbox.
- **Logo** — a square logo, at least 512×512 pixels, and a rectangular one.

> Two of these are not yet available: the contact email and the logo. They are
> marked as TODO in `data/site-config.json`. Google will not approve a
> publication without them, so these must exist before applying.

### Step 4 — point it at our content
1. Open the **Google News** tab inside the publication.
2. Under **Content settings**, add the news sitemap:
   `https://gospelnewsaccess-eng.github.io/gospel-news-access/sitemap-news.xml`

### Step 5 — the pages Google will check
Google will look for pages that show who is behind the publication. All of
these already exist:

| What Google looks for | Our page |
|---|---|
| Who runs this | `/about.html` |
| Who is responsible | `/masthead.html` |
| How to contact them | `/contact.html` |
| How mistakes are handled | `/corrections.html` |
| Ownership and funding | `/about.html` |

### Step 6 — submit for review
Click **Publish** then **Submit for review**. Review takes from a few days to
a few weeks. You will get an email.

> **If you are rejected:** the email says why. The usual reason is not enough
> original reporting. Keep publishing originals and reapply — reapplying is
> allowed and normal.

---

# PART 3 — Bing Webmaster Tools

Bing is much faster than Google and powers DuckDuckGo and ChatGPT search too.
Worth 10 minutes.

### Step 1 — open it
Go to **https://www.bing.com/webmasters** and sign in. You can sign in with the
Google account you just used.

### Step 2 — import from Google (the easy way)
1. Bing offers **Import from Google Search Console**. Click it.
2. Allow access when Google asks.
3. Choose the Gospel News Access property and click **Import**.

That copies the site and the verification across. You are done.

### Step 3 — if the import does not work, do it manually
1. Click **Add a site manually**.
2. Paste `https://gospelnewsaccess-eng.github.io/gospel-news-access/`
3. Choose the **XML file** verification option and upload the file it gives you
   the same way you did for Google in Part 1, Step 3.
4. Then go to **Sitemaps → Submit sitemap** and add both sitemap addresses.

---

# PART 4 — after everything is submitted

### Check these once a week for the first month

| Where | What you are looking for |
|---|---|
| Search Console → **Pages** | How many pages are indexed. It should climb. |
| Search Console → **Sitemaps** | Both should say Success |
| Search Console → **Performance** | What people search to reach you |
| Bing Webmaster → **Site Explorer** | Same thing, faster |

### Things that will hurt the site, so do not do them

- **Do not** submit other publications' stories in the news sitemap. Our news
  sitemap deliberately contains only our own reporting. Submitting somebody
  else's work as ours is the fastest way to be removed from Google News.
- **Do not** buy links or pay for "SEO packages" that promise rankings.
- **Do not** delete the Google verification file.
- **Do not** publish the same story under two different addresses.

### If traffic suddenly disappears
Check Search Console → **Manual actions** first. If it says "No issues
detected", it is almost always a Google algorithm update, not a penalty. Keep
publishing.

---

# What is already done for you

You do not need to set any of this up — it is built into the site and updates
itself:

- `robots.txt` telling search engines what to crawl
- `sitemap.xml` rebuilt on every wire run
- `sitemap-news.xml` holding only our own last-48-hours reporting
- `NewsMediaOrganization` structured data on the front page
- `BreadcrumbList` structured data on section pages
- `ItemList` structured data on the wire
- `NewsArticle` structured data on our own reporting
- `VideoObject` structured data on every video
- Open Graph and Twitter card tags on every page
- Canonical addresses on every page
- The E-E-A-T pages: about, contact, masthead, ownership, corrections
