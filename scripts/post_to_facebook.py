"""
Posts the single oldest pending caption in social/facebook/pending/ to the
PickLoot Facebook Page, then moves that file to social/facebook/posted/ so
it's never posted twice. Zero third-party dependencies (stdlib urllib only)
so it runs on a bare GitHub Actions ubuntu-latest runner with no pip install.

Mirrors scripts/post_to_bluesky.py's queue-drain pattern.

Required environment variables (set as GitHub repo secrets):
  FACEBOOK_PAGE_ID            Numeric Page ID for the PickLoot Facebook Page
  FACEBOOK_PAGE_ACCESS_TOKEN  An access token that can manage the Page. This may
                               be EITHER a Page access token OR a User access
                               token that holds pages_manage_posts for the Page
                               — the script resolves the correct Page token at
                               runtime (see resolve_page_token), so it doesn't
                               matter which type was pasted into the secret.

Caption file format (plain .txt): the caption text as it should appear in the
post, ending with the pickloot.com blog URL. The trailing URL is extracted and
also sent as the Graph API "link" field so Facebook renders a link-preview
card in addition to the inline text link.
"""
import json
import os
import re
import sys
import urllib.parse
import urllib.request
import urllib.error
from pathlib import Path

PENDING_DIR = Path("social/facebook/pending")
POSTED_DIR = Path("social/facebook/posted")
GRAPH_API_VERSION = "v21.0"
GRAPH_BASE = f"https://graph.facebook.com/{GRAPH_API_VERSION}"
MAX_CHARS = 63206  # Facebook's post length limit (generous; captions are short anyway)

URL_PATTERN = re.compile(r"(?:https?://)?(?:www\.)?pickloot\.com(?:/[^\s]*)?")


def extract_link(text):
    """Find the pickloot.com URL in the caption and normalize it to a full https:// URL."""
    m = URL_PATTERN.search(text)
    if not m:
        return None
    display = m.group(0).rstrip(".,)")
    return display if display.startswith("http") else f"https://{display}"


def api_get(path, params):
    url = f"{GRAPH_BASE}/{path}?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"GET {path} failed: HTTP {e.code} {body}") from e


def resolve_page_token(page_id, token):
    """Return a Page access token for page_id, given either a Page or User token.

    We can't tell from the token string alone whether the secret holds a Page
    token or a User token (a common point of confusion when generating tokens in
    the Graph API Explorer). So:
      1. Ask `/{page_id}?fields=access_token` — when `token` is a User token that
         manages the Page, Facebook returns the Page's own access token here.
      2. If that yields a usable token, use it (this is the correct Page token
         and, if the User token was long-lived, is itself long-lived).
      3. Otherwise fall back to the token as-is (it was already a Page token).
    """
    try:
        data = api_get(str(page_id), {"fields": "access_token", "access_token": token})
        page_token = data.get("access_token")
        if page_token:
            print("Resolved a Page access token from the provided token.")
            return page_token
    except RuntimeError as e:
        # Most likely the provided token is already a Page token (which can't read
        # another object's `access_token` field) — fall through and use it directly.
        print(f"Could not derive a Page token ({e}); using the provided token as-is.")
    return token


def post_to_feed(page_id, payload, token):
    url = f"{GRAPH_BASE}/{page_id}/feed"
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

    page_token = resolve_page_token(page_id, token)

    print(f"Posting {target.name} ({len(text)} chars, link={link})...")

    result = post_to_feed(page_id, payload, page_token)
    print(f"Posted: {result.get('id')}")

    target.rename(POSTED_DIR / target.name)
    print(f"Moved {target.name} -> {POSTED_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
