# Switching the forms on

Every form on the site currently shows its fields but **cannot be submitted**,
and says so on the page.

## Why they are switched off

This site is a set of static files. There is no server behind it to catch a
form submission. A form that quietly posts nowhere is worse than no form: an
artist believes they submitted their music, a church believes it asked to be
listed, somebody in need believes they asked for help — and nothing arrived.

So the forms are visibly disabled until a real destination exists.

## The forms

| Page | What it collects | Setting in `data/site-config.json` |
|---|---|---|
| `submit-music.html` | Chart submissions | `music_submission_endpoint` |
| `churches/join.html` | Church listings | `church_join_endpoint` |
| `contact.html` | General contact | `contact_endpoint` |
| `cdc/*.html` | CDC enquiries, service link requests | `cdc_contact_endpoint` |

## How to switch one on

1. Create a form endpoint with a form service. Any of these work and all have a
   free tier: Formspree, Basin, Formsubmit, or a Google Form.
2. The service gives you a web address to post to, like
   `https://formspree.io/f/abcdwxyz`.
3. Open `data/site-config.json`, find the setting in the table above, and
   replace `null` with that address in quotes:

   ```json
   "music_submission_endpoint": "https://formspree.io/f/abcdwxyz",
   ```

4. Commit the change. The form becomes live on the next page build.

## A form endpoint is not a secret

A form endpoint address is public by design — it is visible in the page source
of any site that uses one. It is safe in `data/site-config.json`.

**An API key is not.** If a service gives you a secret key, that goes in GitHub
Secrets (Settings → Secrets and variables → Actions), never in a file.

## The auto-reply for music submissions

Set this up in the form service itself, under autoresponder settings. It must
say two things:

1. Which tracking week the submission falls into — the tracking week runs
   Friday 12:00 AM through Thursday 11:59 PM Pacific, and anything after the
   Thursday cutoff counts in the following week.
2. **That submission does not guarantee charting.** Submissions are 15% of a
   chart position; the rest is reported radio spins and measured streaming
   movement.

Suggested wording:

> Thank you — we have your submission for [ARTIST] – [TRACK].
>
> It will be considered for the tracking week running Friday through Thursday
> Pacific. Submissions received after Thursday 11:59 PM Pacific are considered
> in the following week.
>
> Please note that submitting music does not guarantee charting. Submissions
> count toward one of four measured inputs. How positions are calculated is
> published in full at
> https://gospelnewsaccess-eng.github.io/gospel-news-access/charts/methodology.html
>
> Gospel News Access does not accept payment for chart consideration, chart
> position, or reporter panel membership.

## Where submissions end up

The form service emails them to you. To feed them into the chart, save each one
as a JSON file in `data/submissions/` — the format is in that folder's README.
