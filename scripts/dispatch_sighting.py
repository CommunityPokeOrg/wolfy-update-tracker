#!/usr/bin/env python3
"""wolfy_sighting webhook bridge: receive -> validate -> repository_dispatch.

A tiny stdlib HTTP server that accepts sighting webhooks from chat bots /
bridges (Discord, Matrix, an IRC bouncer, a cron, whatever) and forwards them
to this repo's `repository_dispatch` endpoint so the record-sighting workflow
appends them to the tracker.

Run it anywhere persistent (small VPS, always-on box, fly.io, ...):

    export GH_DISPATCH_TOKEN=<pat-with-repo-or-contents:write>
    export WEBHOOK_SECRET=<shared-secret>          # optional but recommended
    python3 scripts/dispatch_sighting.py --port 8787

Endpoints:
    POST /sighting   JSON body {timestamp, message, source, author_id, author_name}
    GET  /health     returns 200 {"ok": true}

Auth (when WEBHOOK_SECRET is set, one of):
    Authorization: Bearer <WEBHOOK_SECRET>
    X-Hub-Signature-256: sha256=<hmac-sha256 of raw body>

Also usable as a one-shot CLI forwarder for manual testing:

    python3 scripts/dispatch_sighting.py --send \
        '{"timestamp":"2026-09-23T22:31:00+07:00","message":"update the bot",
          "source":"discord","author_id":"123","author_name":"Wolfy"}'

No secrets are stored in the repo — everything comes from the environment.
"""
import argparse
import hashlib
import hmac
import json
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import tracker_text

REPO = os.environ.get("REPO", "CommunityPokeOrg/wolfy-update-tracker")
DISPATCH_URL = f"https://api.github.com/repos/{REPO}/dispatches"
EVENT_TYPE = "wolfy_sighting"
KEYWORDS = tracker_text.load_keywords()

MAX_MESSAGE_LEN = 500
MAX_FIELD_LEN = 64
MAX_BODY = 64 * 1024


def validate(payload):
    """Return an error string, or None if the payload is acceptable."""
    if not isinstance(payload, dict):
        return "body must be a JSON object"
    for key in ("timestamp", "message", "source", "author_name"):
        v = payload.get(key)
        if not isinstance(v, str) or not v.strip():
            return f"'{key}' must be a non-empty string"
    if len(payload["message"]) > MAX_MESSAGE_LEN:
        return f"'message' exceeds {MAX_MESSAGE_LEN} chars"
    if tracker_text.occurrences(payload["message"], KEYWORDS) == 0:
        return "message contains no tracked phrase (keywords.json) — not a sighting"
    author_id = payload.get("author_id")
    if not isinstance(author_id, (str, int)) or isinstance(author_id, bool):
        return "'author_id' must be a string or integer"
    try:
        datetime.fromisoformat(payload["timestamp"].replace("Z", "+00:00"))
    except ValueError:
        return "'timestamp' is not ISO 8601"
    if len(str(author_id)) > MAX_FIELD_LEN or len(payload["source"]) > MAX_FIELD_LEN \
            or len(payload["author_name"]) > MAX_FIELD_LEN:
        return f"field exceeds {MAX_FIELD_LEN} chars"
    return None


def dispatch(payload):
    """POST the payload to GitHub's repository_dispatch API. Returns (ok, info)."""
    token = os.environ.get("GH_DISPATCH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token:
        return False, "GH_DISPATCH_TOKEN not set"
    body = json.dumps({"event_type": EVENT_TYPE, "client_payload": payload}).encode()
    req = urllib.request.Request(DISPATCH_URL, data=body, method="POST", headers={
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "Content-Type": "application/json",
    })
    try:
        with urllib.request.urlopen(req) as res:
            return 200 <= res.status < 300, f"dispatched ({res.status})"
    except urllib.error.HTTPError as e:
        return False, f"GitHub API {e.code}: {e.read()[:200]!r}"
    except OSError as e:
        return False, f"network error: {e}"


class Handler(BaseHTTPRequestHandler):
    secret = os.environ.get("WEBHOOK_SECRET")

    def _json(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _authorized(self, raw):
        if not self.secret:
            return True
        auth = self.headers.get("Authorization", "")
        if auth == f"Bearer {self.secret}":
            return True
        sig = self.headers.get("X-Hub-Signature-256", "")
        if sig.startswith("sha256="):
            want = hmac.new(self.secret.encode(), raw, hashlib.sha256).hexdigest()
            return hmac.compare_digest(sig[7:], want)
        return False

    def do_GET(self):
        if self.path == "/health":
            return self._json(200, {"ok": True, "repo": REPO, "event_type": EVENT_TYPE})
        self._json(404, {"error": "not found"})

    def do_POST(self):
        if self.path != "/sighting":
            return self._json(404, {"error": "not found"})
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = 0
        if length <= 0 or length > MAX_BODY:
            return self._json(400, {"error": "bad content length"})
        raw = self.rfile.read(length)
        if not self._authorized(raw):
            return self._json(401, {"error": "unauthorized"})
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            return self._json(400, {"error": "invalid JSON"})
        err = validate(payload)
        if err:
            return self._json(422, {"error": err})
        ok, info = dispatch(payload)
        self._json(204 if ok else 502, {"ok": ok, "detail": info})

    def log_message(self, fmt, *args):
        sys.stderr.write("bridge %s - %s\n" % (self.address_string(), fmt % args))


def main():
    ap = argparse.ArgumentParser(description="wolfy_sighting webhook bridge")
    ap.add_argument("--port", type=int, default=int(os.environ.get("PORT", "8787")))
    ap.add_argument("--host", default=os.environ.get("HOST", "0.0.0.0"))
    ap.add_argument("--send", metavar="JSON",
                    help="validate + dispatch one payload, then exit")
    args = ap.parse_args()

    if args.send:
        payload = json.loads(args.send)
        err = validate(payload)
        if err:
            sys.exit(f"invalid payload: {err}")
        ok, info = dispatch(payload)
        print(info)
        sys.exit(0 if ok else 1)

    auth = "WEBHOOK_SECRET" if os.environ.get("WEBHOOK_SECRET") else "NONE"
    print(f"listening on {args.host}:{args.port} -> {DISPATCH_URL} (auth: {auth})")
    ThreadingHTTPServer((args.host, args.port), Handler).serve_forever()


if __name__ == "__main__":
    main()
