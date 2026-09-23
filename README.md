# 🐺 Wolfy Update Tracker

**How many times will Wolfy say the word "update" in 24 hours?**
The community counts. The tracker tallies. The grill prints the receipts.

Live site: **https://communitypokeorg.github.io/wolfy-update-tracker/**

## What's on the dashboard

- **Big live ticker** — the total count of "update" utterances, refreshed automatically, with a pace projection ("projected N.N updates by closing time").
- **24-hour countdown** — the tracking window is a fixed 24h measured in **UTC+7**, with a live UTC+7 wall clock and an updates-per-hour sparkline.
- **Over/Under odds board** — pick a line (3.5, 7.5, 13.5, 21.5, 42.5) and vote on the pinned *odds board* issue: **👍 = OVER, 👎 = UNDER**. The page reads the reactions and computes live percentages. Winnings paid in grillikuittis and glory.
- **Ban Risk Multiplier™** — a *purely hypothetical* score computed from community-reported admin/mod messages (warning & ban jokes, e.g. Mia's "Updates" jokes) in the last 48 hours. Shows the multiplier, volatility, and distance to a *notional* mod strike. Not a real moderation decision — see the on-page assumptions.
- **Grillikuitti** — every sighting is printed on the official grill receipt. Sis. ALV 14% päivityksiä. K-Rauta collateral damage included.

## How to participate

| Action | How |
|---|---|
| Wolfy said "update" | Open a [sighting report](../../issues/new?template=sighting.yml) — one issue per sighting, set the count |
| Bet on the total | React 👍 (over) or 👎 (under) on a line comment in the [odds board issue](../../issues?q=label%3Aodds) |
| A mod made a ban joke | File a [mod omen](../../issues/new?template=mod-omen.yml) with a menace level 1–5 |

All data lives in this repo as GitHub issues and reactions — the site is fully static
(GitHub Pages) and reads everything through the public GitHub API.

## How it works

- `index.html` / `style.css` / `app.js` / `config.js` — static site, no build step.
- Sightings: issues labeled `sighting`; the count is parsed from the form's count field.
- Odds: reactions on comments of the issue labeled `odds` (`<!-- line:X.X -->` markers).
- Ban risk: issues labeled `mod-omen` within 48h, menace-weighted with an 18h half-life.
- Polling uses ETag/conditional requests to stay friendly with rate limits.

## Local dev

```bash
python3 -m http.server 8000
# open http://localhost:8000
```

## Disclaimers

This is a community joke project. The Ban Risk Multiplier™ is computed from
self-reported jokes and means nothing officially. Wolfy's fate remains in Wolfy's paws.
