# private/ — NEVER PUBLISHED

Everything in this folder except this README is listed in `.gitignore`, which
means Git is forbidden to upload it. It never reaches GitHub and never reaches
the public website.

## What belongs here

`church-contacts.md` — the working relationship file:

- direct contacts (church office lines, administrator names)
- relationship notes ("met Terry at the 2025 convention", "prefers text")
- outreach history (who was contacted, when, what they said)

## What must NEVER go here or anywhere else in this repository

- Zoom meeting IDs, dial-in numbers, or passwords — including the His Presence
  Fire Thursday service code. These are not published anywhere on the site.
  The site uses a request form instead.
- API keys, tokens, passwords. Those go in GitHub Secrets, never in a file.

## The two-file rule

There are two rosters and they never merge:

| File | Published? | Holds |
|---|---|---|
| `data/churches-public.json` | Yes, renders as `churches.html` | Only what the church itself publishes |
| `private/church-contacts.md` | Never | Everything else |

If a piece of information is not on the church's own public page or supplied
through an opt-in form, it does not go in the public file. Ever.
