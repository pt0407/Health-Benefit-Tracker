#!/usr/bin/env python3
"""Snapshot the official agency pages cited in data/sources/*.json into data/raw/.

The build plan names the Benefits.gov API as the data source. That API was retired:
benefits.gov now redirects to USA.gov and api.benefits.gov does not respond. The records in
data/programs/ are therefore hand-curated from official agency pages, and this tool only saves
those pages so the quoted evidence can be re-checked later (parse_programs.py --check-evidence).
It never reads Benefits.gov and it does not generate records.

Each unique URL is fetched once, with a descriptive User-Agent, a 30 second timeout, one request
per second and at most one retry. Nothing is done to get around 403, 202, 429, CAPTCHA or other
bot checks: such pages are logged as BLOCKED and must be read by hand.

Output lines:
  FETCH <OK|BLOCKED|ERROR> <status or reason> <url>
  SUMMARY urls=<n> ok=<n> blocked=<n> error=<n>
Files go to data/raw/ (gitignored) and the log to data/raw/fetch_log.json. Exit status is 0
unless URLs were listed and none could be fetched.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import httpx  # noqa: E402

from parse_programs import REPO_ROOT, USER_AGENT, host_status, iter_sidecar_fields, urls_of  # noqa: E402

BLOCKED_STATUSES = {202, 401, 403, 429}


def make_client(transport: httpx.BaseTransport | None = None) -> httpx.Client:
    return httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=30.0, follow_redirects=True, transport=transport)


def fetch_one(client: httpx.Client, url: str, raw_dir: Path, delay: float) -> dict:
    """Fetch one URL and return its fetch_log entry (never raises)."""
    entry = {"url": url, "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    if host_status(url) is not None:
        return {**entry, "error": "host-not-allowed"}
    resp, error = None, ""
    for attempt in range(2):
        try:
            resp, error = client.get(url), ""
        except httpx.HTTPError as exc:
            resp, error = None, type(exc).__name__
        if resp is not None and resp.status_code < 500:
            break
        if attempt == 0:
            time.sleep(delay)
    if resp is None:
        return {**entry, "error": error}
    entry.update(status=resp.status_code, final_url=str(resp.url))
    if resp.status_code in BLOCKED_STATUSES:
        return entry
    if resp.status_code != 200 or not resp.content:
        return {**entry, "error": f"http-{resp.status_code}"}
    is_pdf = "pdf" in resp.headers.get("content-type", "").lower() or entry["final_url"].lower().split("?")[0].endswith(".pdf")
    name = hashlib.sha256(url.encode()).hexdigest()[:16] + (".pdf" if is_pdf else ".html")
    (raw_dir / name).write_bytes(resp.content)
    return {**entry, "sha256": hashlib.sha256(resp.content).hexdigest(), "bytes": len(resp.content), "file": name}


def snapshot(data_dir, client: httpx.Client | None = None, delay: float = 1.0) -> dict:
    """Snapshot every unique URL cited in data/sources/*.json; return the SUMMARY counts."""
    raw_dir = Path(data_dir) / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    urls = list(dict.fromkeys(u for _pid, _key, f in iter_sidecar_fields(data_dir) for u in urls_of(f)))
    own = client is None
    client = client or make_client()
    counts = {"urls": len(urls), "ok": 0, "blocked": 0, "error": 0}
    log = []
    for i, url in enumerate(urls):
        if i:
            time.sleep(delay)
        entry = fetch_one(client, url, raw_dir, delay)
        log.append(entry)
        kind = "error" if "error" in entry else "ok" if "file" in entry else "blocked"
        counts[kind] += 1
        print(f"FETCH {kind.upper()} {entry.get('error') or entry['status']} {url}", flush=True)
    if own:
        client.close()
    (raw_dir / "fetch_log.json").write_text(json.dumps(log, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("SUMMARY " + " ".join(f"{k}={v}" for k, v in counts.items()), flush=True)
    return counts


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Snapshot the official pages cited in data/sources/*.json into data/raw/.")
    ap.add_argument("--data-dir", type=Path, default=REPO_ROOT / "data", help="directory holding sources/ and raw/")
    counts = snapshot(ap.parse_args(argv).data_dir)
    return 1 if counts["urls"] and not counts["ok"] else 0


if __name__ == "__main__":
    sys.exit(main())
