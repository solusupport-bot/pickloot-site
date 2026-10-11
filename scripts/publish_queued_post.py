"""
Publishes at most one pre-written guide from data/post_content_queue.json per
run. This script never writes post content itself — see scripts/lib/post_quality.py
for why (ported from land-in-korea's same lesson). A real Claude Code session
fills the queue by actually researching products; this script only checks a
queue entry against the structural gate and, if it passes, turns it into a
published .md file plus a queued Bluesky caption.

Zero third-party dependencies (stdlib only), same convention as the other
scripts/*.py in this repo.
"""
import json
import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib.post_quality import check_post_quality  # noqa: E402

REPO_ROOT = Path(__file__).parent.parent
QUEUE_PATH = REPO_ROOT / "data" / "post_content_queue.json"
POSTS_DIR = REPO_ROOT / "src" / "content" / "posts"
BLUESKY_PENDING_DIR = REPO_ROOT / "social" / "bluesky" / "pending"

LOW_BACKLOG_WARNING_THRESHOLD = 3
MAX_GRAPHEMES = 300  # mirror post_to_bluesky.py's Bluesky limit


def load_queue():
    if not QUEUE_PATH.exists():
        return {}
    return json.loads(QUEUE_PATH.read_text(encoding="utf-8"))


def already_published_slugs():
    POSTS_DIR.mkdir(parents=True, exist_ok=True)
    return {p.stem for p in POSTS_DIR.glob("*.md")}


def build_frontmatter(slug, post):
    lines = ["---"]
    lines.append(f'title: "{post["title"]}"')
    lines.append(f'description: "{post["description"]}"')
    lines.append(f"publishDate: {date.today().isoformat()}")
    lines.append(f'category: "{post["category"]}"')
    lines.append('format: "guide"')
    for key in ("heroImage", "heroImageAlt", "heroImageCreditName", "heroImageCreditUrl"):
        if post.get(key):
            lines.append(f'{key}: "{post[key]}"')
    lines.append("draft: false")
    lines.append("specs:")
    specs = post["specs"]
    lines.append(f"  columns: {json.dumps(specs['columns'])}")
    lines.append("  options:")
    for opt in specs["options"]:
        lines.append(f'    - name: "{opt["name"]}"')
        if opt.get("tier"):
            lines.append(f'      tier: "{opt["tier"]}"')
        if opt.get("amazonUrl"):
            lines.append(f'      amazonUrl: "{opt["amazonUrl"]}"')
        lines.append("      values:")
        for v in opt["values"]:
            lines.append(f'        - "{v}"')
        if opt.get("fitsWhen"):
            lines.append(f'      fitsWhen: "{opt["fitsWhen"]}"')
    lines.append("---")
    lines.append("")
    return "\n".join(lines)


def build_bluesky_caption(slug, post):
    url = f"pickloot.com/blog/{slug}/"
    hook = post["description"].strip()
    budget = MAX_GRAPHEMES - len(url) - 2
    if len(hook) > budget:
        hook = hook[: budget - 1].rstrip() + "…"
    return f"{hook}: {url}"


def queue_bluesky_caption(slug, post):
    BLUESKY_PENDING_DIR.mkdir(parents=True, exist_ok=True)
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    existing = list(BLUESKY_PENDING_DIR.glob(f"{today}-*.txt"))
    seq = len(existing) + 1
    target = BLUESKY_PENDING_DIR / f"{today}-{seq:02d}-{slug}.txt"
    target.write_text(build_bluesky_caption(slug, post), encoding="utf-8")
    return target


def main():
    queue = load_queue()
    published = already_published_slugs()
    pending_slugs = [slug for slug in queue if slug not in published]

    if not pending_slugs:
        print("Queue is empty or everything in it is already published. Nothing to do.")
        return 0

    publishable = []
    rejected = []
    for slug in pending_slugs:
        problems = check_post_quality(queue[slug])
        if problems:
            rejected.append((slug, problems))
        else:
            publishable.append(slug)

    for slug, problems in rejected:
        print(f"Skipping {slug!r} — failed quality gate: {'; '.join(problems)}")

    if not publishable:
        print("No queued post passes the quality gate. Nothing published today.")
        return 0

    slug = publishable[0]
    post = queue[slug]
    target = POSTS_DIR / f"{slug}.md"
    target.write_text(build_frontmatter(slug, post) + post["body"].strip() + "\n", encoding="utf-8")
    print(f"Published: {target}")

    caption_path = queue_bluesky_caption(slug, post)
    print(f"Queued Bluesky caption: {caption_path}")

    remaining = len(publishable) - 1
    if remaining <= LOW_BACKLOG_WARNING_THRESHOLD:
        print(f"WARNING: only {remaining} publishable guide(s) left in the queue — write more soon.")
    else:
        print(f"Publishable backlog remaining: {remaining}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
