#!/usr/bin/env python3
"""Record a wolfy_sighting repository_dispatch payload.

Reads the client_payload from the GitHub Actions event (GITHUB_EVENT_PATH),
validates it, appends the sighting to data/sightings.json, and updates the
webhook counters in data/stats.json. Exit non-zero on invalid payloads so the
workflow fails loudly instead of committing garbage.

Payload contract (client_payload):
  timestamp    ISO 8601 string, when Wolfy said it (e.g. "2026-09-23T22:31:00+07:00")
  message      the message containing "update" (string, 1-500 chars)
  source       where it came from, e.g. "discord" (string, 1-64 chars)
  author_id    stable author id from the source platform (string/int, -> str)
  author_name  display name (string, 1-64 chars)

The "update count" contributed by a sighting is the number of word-boundary
'update' occurrences in `message` (case-insensitive). A payload whose message
contains zero occurrences is rejected.
"""
import json
import os
import re
import sys
from datetime import datetime, timezone

DATA_DIR = "data"
SIGHTINGS_FILE = os.path.join(DATA_DIR, "sightings.json")
STATS_FILE = os.path.join(DATA_DIR, "stats.json")

MAX_MESSAGE_LEN = 500
MAX_FIELD_LEN = 64
UPDATE_RE = re.compile(r"\bupdate\b", re.IGNORECASE)


def fail(msg):
    print(f"::error::invalid wolfy_sighting payload: {msg}", file=sys.stderr)
    sys.exit(1)


def require_str(payload, key, maxlen):
    v = payload.get(key)
    if not isinstance(v, str) or not v.strip():
        fail(f"'{key}' must be a non-empty string")
    if len(v) > maxlen:
        fail(f"'{key}' exceeds {maxlen} chars")
    return v.strip()


def parse_timestamp(v):
    if not isinstance(v, str) or not v.strip():
        fail("'timestamp' must be an ISO 8601 string")
    try:
        dt = datetime.fromisoformat(v.strip().replace("Z", "+00:00"))
    except ValueError:
        fail(f"'timestamp' is not ISO 8601: {v!r}")
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


def load_json(path, default):
    try:
        with open(path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def main():
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    if event_path and os.path.exists(event_path):
        event = json.load(open(event_path))
        payload = event.get("client_payload") or {}
    else:
        # Local testing: read the payload from stdin.
        payload = json.load(sys.stdin)
    if not isinstance(payload, dict):
        fail("client_payload must be a JSON object")

    message = require_str(payload, "message", MAX_MESSAGE_LEN)
    source = require_str(payload, "source", MAX_FIELD_LEN)
    author_name = require_str(payload, "author_name", MAX_FIELD_LEN)

    author_id = payload.get("author_id")
    if not isinstance(author_id, (str, int)) or isinstance(author_id, bool):
        fail("'author_id' must be a string or integer")
    author_id = str(author_id)
    if not author_id or len(author_id) > MAX_FIELD_LEN:
        fail(f"'author_id' must be 1-{MAX_FIELD_LEN} chars")

    timestamp = parse_timestamp(payload.get("timestamp"))

    count = len(UPDATE_RE.findall(message))
    if count == 0:
        fail("message contains no 'update' — not a sighting")

    sighting = {
        "timestamp": timestamp,
        "message": message,
        "source": source,
        "author_id": author_id,
        "author_name": author_name,
        "count": count,
        "received_at": datetime.now(timezone.utc).isoformat(),
    }

    os.makedirs(DATA_DIR, exist_ok=True)
    sightings = load_json(SIGHTINGS_FILE, [])
    if not isinstance(sightings, list):
        fail("data/sightings.json is not a list — refusing to clobber")
    sightings.append(sighting)
    with open(SIGHTINGS_FILE, "w") as f:
        json.dump(sightings, f, indent=2, ensure_ascii=False)

    stats = load_json(STATS_FILE, {})
    webhook = stats.get("webhook", {})
    webhook["events"] = webhook.get("events", 0) + 1
    webhook["updates"] = webhook.get("updates", 0) + count
    webhook["last_sighting_at"] = sighting["timestamp"]
    by_source = webhook.get("by_source", {})
    by_source[source] = by_source.get(source, 0) + count
    webhook["by_source"] = by_source
    stats["webhook"] = webhook
    stats["total_updates"] = stats.get("issue_updates", 0) + webhook["updates"]
    stats["updated_at"] = sighting["received_at"]
    with open(STATS_FILE, "w") as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)

    print(f"recorded sighting: {count} update(s) by {author_name} via {source}"
          f" (webhook totals: {webhook['events']} events / {webhook['updates']} updates)")


if __name__ == "__main__":
    main()
