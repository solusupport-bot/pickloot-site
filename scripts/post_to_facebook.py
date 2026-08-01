"""
Posts the single oldest pending caption in social/facebook/pending/ to the
PickLoot Facebook Page, then moves that file to social/facebook/posted/ so
it's never posted twice. Zero third-party dependencies (stdlib urllib only)
so it runs on a bare GitHub Actions ubuntu-latest runner with no pip install.

Mirrors scripts/post_to_bluesky.py's queue-drain pattern.

Required environment variables (set as GitHub repo secrets):
  FACEBOOK_PAGE_ID            Numeric Page ID for the PickLoot Facebook Page
  FACEBOOK_PAGE_ACCESS_TOKEN  A long-lived (or never-expiring) Page Access Token
                               with pages_manage_posts permission

Caption file format (plain .txt): the caption text as it should appear in the
post, ending with the pickloot.com blog URL. The trailing URL is extracted and
also sent as the Graph API "link" field so Facebook renders a link-preview
card in addition to the inline text link.
"""
import json
import os
import re
import sys
import urllib.request
import urllib.error
from pathlib import Path

PENDING_DIR = Path("social/facebook/pending")
POSTED_DIR = Path("social/facebook/posted")
GRAPH_API_VERSION = "v21.0"
MAX_CHARS = 63206  # Facebook's post length limit (generous; captions are short anyway)

URL_PATTERN = re.compile(r"(?:https?://)?(?:www\.)?pickloot\.com(?:/[^\s]*)?")


def extract_link(text):
    """Find the pickloot.com URL in the caption and normalize it to a full https:// URL."""
    m = URL_PATTERN.search(text)
    if not m:
        return None
    display = m.group(0).rstrip(".,)")
    return display if display.startswith("http") else f"https://{display}"


def api_post(page_id, payload, token):
    import urllib.parse

    url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{page_id}/feed"
    payload = dict(payload)
    payload["access_token"] = token
    data = urllib.parse.urlencode(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Facebook feed post failed: HTTP {e.code} {body}") from e


def main():
    page_id = os.environ.get("FACEBOOK_PAGE_ID")
    token = os.environ.get("FACEBOOK_PAGE_ACCESS_TOKEN")
    if not page_id or not token:
        print("FACEBOOK_PAGE_ID / FACEBOOK_PAGE_ACCESS_TOKEN not set — skipping.")
        return 0

    PENDING_DIR.mkdir(parents=True, exist_ok=True)
    POSTED_DIR.mkdir(parents=True, exist_ok=True)

    pending = sorted(PENDING_DIR.glob("*.txt"))
    if not pending:
        print("No pending Facebook posts in queue. Nothing to do.")
        return 0

    target = pending[0]
    text = target.read_text(encoding="utf-8").strip()
    if len(text) > MAX_CHARS:
        text = text[: MAX_CHARS - 1].rstrip() + "…"

    link = extract_link(text)
    payload = {"message": text}
    if link:
        payload["link"] = link

    print(f"Posting {target.name} ({len(text)} chars, link={link})...")

    result = api_post(page_id, payload, token)
    print(f"Posted: {result.get('id')}")

    target.rename(POSTED_DIR / target.name)
    print(f"Moved {target.name} -> {POSTED_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
