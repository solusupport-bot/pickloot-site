#!/usr/bin/env python3
"""
Pull PickLoot's Google Search Console performance into the repo.

Why this lives here rather than in an assistant's scheduled task: the report
ends up as a committed JSON + Markdown file in a public repo, so any later
session can read the numbers with a plain `git pull` and no credentials at
all. The only secret involved stays in GitHub Actions.

Setup (one time, by the site owner):
  1. Google Cloud console → create a project (or reuse one) → enable the
     "Google Search Console API".
  2. Create a service account, then create a JSON key for it and download it.
  3. Search Console → pickloot.com property → Settings → Users and permissions
     → add the service account's email address with "Full" permission.
  4. GitHub → repo Settings → Secrets and variables → Actions → new secret
     GSC_SERVICE_ACCOUNT_JSON, pasting the whole JSON key file as the value.

Reads:
  GSC_SERVICE_ACCOUNT_JSON  service account key, full JSON
  GSC_SITE_URL              property URL, defaults to https://pickloot.com/
                            (use "sc-domain:pickloot.com" for a Domain property)

Writes:
  logs/search-console/<end-date>.json   machine-readable snapshot
  logs/search-console/latest.md         human-readable summary, overwritten
"""

import json
import os
import sys
from datetime import date, timedelta
from pathlib import Path

try:
    from google.oauth2 import service_account
    from google.auth.transport.requests import AuthorizedSession
except ImportError:
    sys.exit("missing dependency: pip install google-auth requests")

SCOPES = ["https://www.googleapis.com/auth/webmasters.readonly"]
API = "https://searchconsole.googleapis.com/webmasters/v3/sites/{site}/searchAnalytics/query"

# Search Console data lags ~2-3 days; ending the window 3 days back keeps the
# most recent figures from looking like a drop that is really just latency.
LAG_DAYS = 3
WINDOW_DAYS = 28


def query(session, site_url, start, end, dimensions, limit=25):
    import urllib.parse

    url = API.format(site=urllib.parse.quote(site_url, safe=""))
    body = {
        "startDate": start.isoformat(),
        "endDate": end.isoformat(),
        "dimensions": dimensions,
        "rowLimit": limit,
    }
    resp = session.post(url, json=body)
    if resp.status_code != 200:
        sys.exit(f"Search Console API {resp.status_code}: {resp.text[:400]}")
    return resp.json().get("rows", [])


def totals(rows):
    return {
        "clicks": sum(r.get("clicks", 0) for r in rows),
        "impressions": sum(r.get("impressions", 0) for r in rows),
    }


def main():
    raw = os.environ.get("GSC_SERVICE_ACCOUNT_JSON")
    if not raw:
        sys.exit("GSC_SERVICE_ACCOUNT_JSON is not set")
    site_url = os.environ.get("GSC_SITE_URL", "https://pickloot.com/")

    creds = service_account.Credentials.from_service_account_info(
        json.loads(raw), scopes=SCOPES
    )
    session = AuthorizedSession(creds)

    end = date.today() - timedelta(days=LAG_DAYS)
    start = end - timedelta(days=WINDOW_DAYS - 1)
    prev_end = start - timedelta(days=1)
    prev_start = prev_end - timedelta(days=WINDOW_DAYS - 1)

    by_date = query(session, site_url, start, end, ["date"], limit=100)
    prev_by_date = query(session, site_url, prev_start, prev_end, ["date"], limit=100)
    top_queries = query(session, site_url, start, end, ["query"], limit=25)
    top_pages = query(session, site_url, start, end, ["page"], limit=25)

    now, before = totals(by_date), totals(prev_by_date)
    snapshot = {
        "generatedOn": date.today().isoformat(),
        "siteUrl": site_url,
        "window": {"start": start.isoformat(), "end": end.isoformat(), "days": WINDOW_DAYS},
        "totals": now,
        "previousWindow": {
            "start": prev_start.isoformat(),
            "end": prev_end.isoformat(),
            "totals": before,
        },
        "indexedPagesWithImpressions": len(top_pages),
        "topQueries": [
            {
                "query": r["keys"][0],
                "clicks": r.get("clicks", 0),
                "impressions": r.get("impressions", 0),
                "position": round(r.get("position", 0), 1),
            }
            for r in top_queries
        ],
        "topPages": [
            {
                "page": r["keys"][0],
                "clicks": r.get("clicks", 0),
                "impressions": r.get("impressions", 0),
                "position": round(r.get("position", 0), 1),
            }
            for r in top_pages
        ],
        "daily": [
            {"date": r["keys"][0], "clicks": r.get("clicks", 0), "impressions": r.get("impressions", 0)}
            for r in by_date
        ],
    }

    out_dir = Path("logs/search-console")
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{end.isoformat()}.json").write_text(
        json.dumps(snapshot, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    def delta(a, b):
        if b == 0:
            return "n/a (previous window was zero)" if a == 0 else f"+{a} from zero"
        return f"{a - b:+d} ({(a - b) / b * 100:+.0f}%)"

    lines = [
        f"# Search Console — {start} to {end}",
        "",
        f"_Generated {date.today()}. Window is {WINDOW_DAYS} days ending {LAG_DAYS} days back,",
        "because Search Console data lags by about that much._",
        "",
        f"- **Impressions:** {now['impressions']} — {delta(now['impressions'], before['impressions'])} vs the previous {WINDOW_DAYS} days",
        f"- **Clicks:** {now['clicks']} — {delta(now['clicks'], before['clicks'])}",
        f"- **Pages with at least one impression:** {len(top_pages)}",
        "",
    ]

    if top_queries:
        lines += ["## Top queries", "", "| Query | Impressions | Clicks | Avg position |", "|---|---:|---:|---:|"]
        lines += [
            f"| {q['query']} | {q['impressions']} | {q['clicks']} | {q['position']} |"
            for q in snapshot["topQueries"][:10]
        ]
        lines.append("")
    else:
        lines += ["## Top queries", "", "No queries returned any impressions in this window.", ""]

    if top_pages:
        lines += ["## Top pages", "", "| Page | Impressions | Clicks | Avg position |", "|---|---:|---:|---:|"]
        lines += [
            f"| {p['page']} | {p['impressions']} | {p['clicks']} | {p['position']} |"
            for p in snapshot["topPages"][:10]
        ]
        lines.append("")

    (out_dir / "latest.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"impressions={now['impressions']} clicks={now['clicks']} pages={len(top_pages)}")


if __name__ == "__main__":
    main()
