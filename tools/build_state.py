#!/usr/bin/env python3
"""Snapshot tracker state to data/state.json (fallback feed when the
visitor's IP is GitHub-API-rate-limited). Runs in GitHub Actions with GITHUB_TOKEN."""
import json, os, re, urllib.request

OWNER, REPO = "CommunityPokeOrg", "wolfy-update-tracker"
API = f"https://api.github.com/repos/{OWNER}/{REPO}"
TOKEN = os.environ["GITHUB_TOKEN"]

def get(path):
    req = urllib.request.Request(API + path, headers={
        "Authorization": f"Bearer {TOKEN}",
        "Accept": "application/vnd.github+json"})
    return json.load(urllib.request.urlopen(req))

def field(body, label):
    m = re.search(rf"###\s*{label}[^\n]*\n([\s\S]*?)(?=\n###|$)", body or "", re.I)
    return m.group(1).strip() if m else ""

def first_int(text, fallback):
    m = re.search(r"\d+", text or "")
    return int(m.group()) if m else fallback

def issues_by_label(label):
    return [i for i in get(f"/issues?labels={label}&state=all&per_page=100")
            if "pull_request" not in i]

def load_json(path, default):
    try:
        with open(path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default

issue_sightings = [{
    "n": i["number"], "title": i["title"],
    "who": (i.get("user") or {}).get("login", "anonymous"),
    "at": i["created_at"],
    "count": first_int(field(i.get("body"), "How many"), 1),
    "quote": field(i.get("body"), "What did Wolfy say").strip('"'),
    "src": "issue",
} for i in issues_by_label("sighting")]

# Webhook sightings recorded via repository_dispatch (data/sightings.json).
webhook_sightings = [{
    "n": f"wh-{idx}", "title": s.get("message", ""),
    "who": s.get("author_name", "anonymous"),
    "at": s.get("timestamp"),
    "count": int(s.get("count", 1)),
    "quote": s.get("message", ""),
    "src": s.get("source", "webhook"),
} for idx, s in enumerate(load_json("data/sightings.json", []))
   if isinstance(s, dict)]

sightings = sorted(issue_sightings + webhook_sightings,
                   key=lambda s: s["at"] or "", reverse=True)

omens = [{
    "n": i["number"],
    "mod": field(i.get("body"), "Which mod") or "a mod",
    "text": field(i.get("body"), "What did they say"),
    "menace": max(1, min(5, first_int(field(i.get("body"), "Menace level"), 3))),
    "at": i["created_at"],
} for i in issues_by_label("mod-omen")]

odds = {}
boards = [i for i in get("/issues?labels=odds&state=open&per_page=5")
          if "pull_request" not in i]
if boards:
    board = boards[0]
    for c in get(f"/issues/{board['number']}/comments?per_page=100"):
        m = re.search(r"<!--\s*line:([\d.]+)\s*-->", c.get("body") or "")
        if m:
            r = c.get("reactions") or {}
            odds[m.group(1)] = {"over": r.get("+1", 0), "under": r.get("-1", 0)}
    state_board = board["number"]
else:
    state_board = None

from datetime import datetime, timezone
issue_updates = sum(s["count"] for s in issue_sightings)
webhook_updates = sum(s["count"] for s in webhook_sightings)
last_at = max((s["at"] for s in sightings if s["at"]), default=None)

state = {
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "board_issue": state_board,
    "sightings": sightings,
    "omens": omens,
    "odds": odds,
}
os.makedirs("data", exist_ok=True)
with open("data/state.json", "w") as f:
    json.dump(state, f, indent=2)

# stats.json: issue-side counters are owned by this script; webhook_* fields
# are owned by scripts/record_sighting.py (preserve whatever is there).
stats = load_json("data/stats.json", {})
stats["issue_sightings"] = len(issue_sightings)
stats["issue_updates"] = issue_updates
stats["webhook_updates"] = webhook_updates
stats["webhook_sightings"] = len(webhook_sightings)
stats["total_updates"] = issue_updates + webhook_updates
stats["last_sighting_at"] = last_at
stats["updated_at"] = datetime.now(timezone.utc).isoformat()
with open("data/stats.json", "w") as f:
    json.dump(stats, f, indent=2)
print(f"state: {len(sightings)} sightings, {len(omens)} omens, {len(odds)} lines; "
      f"stats: {stats['total_updates']} total updates")
