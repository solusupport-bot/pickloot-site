"""
Posts the single oldest pending caption in social/bluesky/pending/ to Bluesky,
then moves that file to social/bluesky/posted/ so it's never posted twice.
Zero third-party dependencies (stdlib urllib only) so it runs on a bare
GitHub Actions ubuntu-latest runner with no pip install step.

Required environment variables (set as GitHub repo secrets):
  BLUESKY_HANDLE        e.g. pickloot.bsky.social
  BLUESKY_APP_PASSWORD  e.g. xxxx-xxxx-xxxx-xxxx (an App Password, not the account password)
"""
import json
import os
import re
import sys
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime, timezone

PENDING_DIR = Path("social/bluesky/pending")
POSTED_DIR = Path("social/bluesky/posted")
API_BASE = "https://bsky.social/xrpc"
MAX_GRAPHEMES = 300  # Bluesky's post length limit


def api_post(endpoint, payload, token=None):
    url = f"{API_BASE}/{endpoint}"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{endpoint} failed: HTTP {e.code} {body}") from e


def build_link_facets(text):
    """Bluesky doesn't auto-linkify URLs — we have to supply byte-offset facets ourselves.

    Captions are written as bare domains without a scheme (e.g. "pickloot.com/blog/x/"),
    so this matches both scheme-full (https://...) and scheme-less (pickloot.com/...)
    mentions of the site, and always resolves the facet's target URI to a full https://
    link regardless of how it's displayed in the post text.
    """
    facets = []
    pattern = re.compile(r"(?:https?://)?(?:www\.)?pickloot\.com(?:/[^\s]*)?")
    for m in pattern.finditer(text):
        display = m.group(0).rstrip(".,)")
        if not display:
            continue
        url = display if display.startswith("http") else f"https://{display}"
        start_char = m.start()
        end_char = start_char + len(display)
        byte_start = len(text[:start_char].encode("utf-8"))
        byte_end = len(text[:end_char].encode("utf-8"))
        facets.append({
            "index": {"byteStart": byte_start, "byteEnd": byte_end},
            "features": [{"$type": "app.bsky.richtext.facet#link", "uri": url}],
        })
    return facets


def main():
    handle = os.environ.get("BLUESKY_HANDLE")
    app_password = os.environ.get("BLUESKY_APP_PASSWORD")
    if not handle or not app_password:
        print("BLUESKY_HANDLE / BLUESKY_APP_PASSWORD not set — skipping.")
        return 0

    PENDING_DIR.mkdir(parents=True, exist_ok=True)
    POSTED_DIR.mkdir(parents=True, exist_ok=True)

    pending = sorted(PENDING_DIR.glob("*.txt"))
    if not pending:
        print("No pending Bluesky posts in queue. Nothing to do.")
        return 0

    target = pending[0]
    text = target.read_text(encoding="utf-8").strip()
    if len(text) > MAX_GRAPHEMES:
        text = text[: MAX_GRAPHEMES - 1].rstrip() + "…"

    print(f"Posting {target.name} ({len(text)} chars)...")

    session = api_post("com.atproto.server.createSession", {
        "identifier": handle,
        "password": app_password,
    })
    access_jwt = session["accessJwt"]
    did = session["did"]

    record = {
        "$type": "app.bsky.feed.post",
        "text": text,
        "createdAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        "langs": ["en"],
    }
    facets = build_link_facets(text)
    if facets:
        record["facets"] = facets

    result = api_post("com.atproto.repo.createRecord", {
        "repo": did,
        "collection": "app.bsky.feed.post",
        "record": record,
    }, token=access_jwt)

    print(f"Posted: {result.get('uri')}")

    POSTED_DIR.mkdir(parents=True, exist_ok=True)
    target.rename(POSTED_DIR / target.name)
    print(f"Moved {target.name} -> {POSTED_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
