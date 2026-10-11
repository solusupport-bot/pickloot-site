"""
Structural hard gate for queued guide posts, run before anything is published
automatically. Ported from land-in-korea's lib/publishing/blog_quality.js —
same incident that script's comments describe (a credit-exhausted LLM call
silently fell back to a short template post that still got auto-published)
is exactly what this gate exists to make impossible here: the automation
script never writes content itself, it only publishes queue entries that
already pass every check below.

No network calls, no API keys — pure structural checks so a bad queue entry
fails loudly and immediately instead of silently.
"""
import re

MIN_BODY_WORDS = 500
MIN_SPEC_COLUMNS = 3
MIN_SPEC_OPTIONS = 3
TITLE_LEN = (50, 60)
DESCRIPTION_LEN = (120, 160)

# content.config.ts on the 'guide' format: "Deliberately carries no price
# column: PickLoot has no live pricing feed, and a hardcoded figure goes
# stale and breaks affiliate-program rules." This regex is that rule
# enforced as a gate instead of a comment someone has to remember.
PRICE_PATTERN = re.compile(r"\$\s?\d")


def _count_words(text):
    return len(re.findall(r"\S+", text or ""))


def check_post_quality(post):
    """Returns a list of problem strings; empty list means the post is publishable."""
    problems = []

    if post.get("format") != "guide":
        problems.append(f"format must be 'guide', got {post.get('format')!r} (legacy 'comparison' format carries hardcoded prices)")

    title = post.get("title") or ""
    if not (TITLE_LEN[0] <= len(title) <= TITLE_LEN[1]):
        problems.append(f"title length {len(title)} chars (need {TITLE_LEN[0]}-{TITLE_LEN[1]})")

    description = post.get("description") or ""
    if not (DESCRIPTION_LEN[0] <= len(description) <= DESCRIPTION_LEN[1]):
        problems.append(f"description length {len(description)} chars (need {DESCRIPTION_LEN[0]}-{DESCRIPTION_LEN[1]})")

    body = post.get("body") or ""
    words = _count_words(body)
    if words < MIN_BODY_WORDS:
        problems.append(f"body word count {words} < {MIN_BODY_WORDS}")
    if len(re.findall(r"^## ", body, re.MULTILINE)) < 3:
        problems.append("fewer than 3 '## ' subheadings in body")
    if re.search(r"^# ", body, re.MULTILINE):
        problems.append("body uses an H1 (# ) — should start at H2")

    specs = post.get("specs") or {}
    columns = specs.get("columns") or []
    options = specs.get("options") or []
    if len(columns) < MIN_SPEC_COLUMNS:
        problems.append(f"specs.columns has {len(columns)} entries (need >= {MIN_SPEC_COLUMNS})")
    if len(options) < MIN_SPEC_OPTIONS:
        problems.append(f"specs.options has {len(options)} entries (need >= {MIN_SPEC_OPTIONS})")
    for opt in options:
        name = opt.get("name", "<unnamed>")
        if not opt.get("amazonUrl"):
            problems.append(f"option {name!r} missing amazonUrl")
        if not opt.get("fitsWhen"):
            problems.append(f"option {name!r} missing fitsWhen")
        values = opt.get("values") or []
        if len(values) != len(columns):
            problems.append(f"option {name!r} has {len(values)} values but specs.columns has {len(columns)}")

    price_haystack = body + "\n" + "\n".join(
        v for opt in options for v in (opt.get("values") or [])
    )
    price_hits = PRICE_PATTERN.findall(price_haystack)
    if price_hits:
        problems.append(f"found {len(price_hits)} hardcoded-looking price token(s) (e.g. '$199') — PickLoot has no live pricing feed, use specs.options[].tier instead")

    return problems
