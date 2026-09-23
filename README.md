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
- `data/sightings.json` — append-only log of webhook sightings (see below).
- `data/stats.json` — live counters (issue + webhook + total updates).
- `data/state.json` — public snapshot the dashboard falls back to when a visitor's
  IP is out of anonymous GitHub API quota. Rebuilt by `refresh-state.yml` on every
  issue/comment event and every 10 minutes.

## 🤖 Webhook bridge — automatic sighting ingestion

Bots (Discord/Matrix/IRC/...) can report sightings straight into the tracker
without a GitHub issue:

```
chat bot ──POST──> scripts/dispatch_sighting.py ──> repository_dispatch
        (anywhere)      (validation + auth)              │
            .github/workflows/record-sighting.yml        │
            validates client_payload, appends to data/sightings.json,
            rebuilds data/state.json + data/stats.json, commits to main
                                                           │
                                          Pages redeploys (~1 min) ──> live dashboard
```

### Bridge setup

1. Run the forwarder somewhere persistent (VPS, always-on box, fly.io…). Stdlib only:
   ```bash
   export GH_DISPATCH_TOKEN=<token>   # classic PAT with `repo` scope, or a
                                     # fine-grained PAT with Contents: write on this repo
   export WEBHOOK_SECRET=<secret>     # optional but recommended
   python3 scripts/dispatch_sighting.py --port 8787
   ```
2. Point your bot at `POST http://<bridge>:8787/sighting` with header
   `Authorization: Bearer <WEBHOOK_SECRET>` (or GitHub-style
   `X-Hub-Signature-256` HMAC over the raw body).
3. One-shot test without a server:
   ```bash
   python3 scripts/dispatch_sighting.py --send \
     '{"timestamp":"2026-09-23T22:31:00+07:00","message":"update the bot",
       "source":"discord","author_id":"123","author_name":"Wolfy"}'
   ```

### Payload shape (client_payload)

| field | type | required | notes |
|---|---|---|---|
| `timestamp` | ISO 8601 string | ✅ | when Wolfy said it (`Z` or offset) |
| `message` | string ≤500 | ✅ | must contain the word `update`; each word-boundary occurrence counts |
| `source` | string ≤64 | ✅ | e.g. `discord`, `matrix` |
| `author_id` | string/int ≤64 | ✅ | stable id from the source platform |
| `author_name` | string ≤64 | ✅ | display name |

Validation happens twice (bridge → workflow), so bad payloads can't land in the
data files. The count a sighting contributes = number of `update` occurrences in
`message` — a message with zero is rejected.

### Limitations

- **Latency:** the workflow commit deploys to Pages in roughly 1–2 minutes. The
  ticker is therefore "near-real-time", not instant.
- **Fire-and-forget:** `repository_dispatch` returns 204; the bridge can't see
  the workflow result. Check Actions runs if something looks missing.
- **No deduplication:** two identical dispatches record two sightings. Include a
  unique-ish `timestamp`/`message` pair or dedupe upstream.
- **Serialized writes:** concurrent dispatches are queued via a concurrency
  group; bursts are handled but slowly.
- **Capacity:** `data/sightings.json` is append-only — fine for a meme tracker,
  not for Big Wolfy Data.
- **Token scope:** `GH_DISPATCH_TOKEN` never enters the repo or the workflow;
  it lives only in the bridge host's environment.

## Local dev

```bash
python3 -m http.server 8000
# open http://localhost:8000
```

## Disclaimers

This is a community joke project. The Ban Risk Multiplier™ is computed from
self-reported jokes and means nothing officially. Wolfy's fate remains in Wolfy's paws.
