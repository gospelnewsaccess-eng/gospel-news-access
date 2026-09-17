# data/reports/ — weekly spin reports from the reporter panel

One folder per tracking week, named for that week's **Friday**:

```
data/reports/2026-09-11/WPRAISE-FM.json
data/reports/2026-09-11/KGSPL.json
```

The tracking week is Friday 12:00 AM Pacific through Thursday 11:59 PM Pacific.
Submission cutoff is Thursday 11:59 PM Pacific.

## The format

```json
{
  "station": "WPRAISE-FM",
  "chart_week": "2026-09-11",
  "spins": [
    { "title": "Song title", "artist": "Artist name",
      "label": "Label name or Independent",
      "chart": "gospel", "spins": 42 }
  ]
}
```

`chart` is one of `gospel`, `christian` or `album`.

## Two rules the script enforces for you

1. **A report from a station that is not on the public panel is ignored.**
   Every reporter is named on `charts/panel.html`. An anonymous report cannot
   be checked by anybody, so it is not allowed to move a chart. Add the station
   to `data/reporters.json` first.

2. **Spins are weighted by station tier**, not counted raw — a station reaching
   two million people and one reaching eight thousand are not the same event.
   The tier weighting is published on `charts/methodology.html`.
