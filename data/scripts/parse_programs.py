#!/usr/bin/env python3
"""Validate the hand-curated benefit records in data/programs/*.json.

The records are written by people from official agency pages. This script does not generate
them: it checks each record against models.program.Program, the data conventions in
data/scripts/README.md, and the per-field sources in data/sources/<name>_sources.json.

Output lines:
  PROBLEM <program_id> <field>: <message>
  UNCONFIRMED <program_id> <field>                                       (allowed, listed)
  EVIDENCE <FOUND|NOT_FOUND|NO_SNAPSHOT> <program_id> <field> <url>      (--check-evidence)
  URL <status> <program_id> <url>                                        (--check-urls)
  SUMMARY programs=<n> problems=<n>
Exit status is 1 only when problems > 0; the EVIDENCE and URL lines are advisory.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import unicodedata
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "backend"))

import httpx  # noqa: E402
from pydantic import ValidationError  # noqa: E402

from models.program import Eligibility, Program  # noqa: E402

USER_AGENT = "BenefitsFinder-data-snapshot/0.1 (+https://github.com/pt0407/Health-Benefit-Tracker)"
CATEGORIES = {"nutrition", "health", "cash", "disability", "energy", "employment"}
EXTRA_HOSTS = {"yourtexasbenefits.com", "www.yourtexasbenefits.com", "texaswic.org", "www.texaswic.org"}
SUFFIX = {"federal_programs.json": "_federal", "texas_programs.json": "_tx"}
BOOL_FIELDS = {f"eligibility.{k}" for k in ("citizenship_required", "requires_children", "requires_disability", "requires_pregnancy")}
NO_EVIDENCE = {"description", "application_url", "documents_needed"}
EM_DASH = chr(0x2014)
_QUOTES = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"', "–": "-"})


def host_status(url: str) -> str | None:
    """None when url is https on an allowed official host (Appendix A6), else the reason."""
    try:
        parts = urlparse(url)
        host = (parts.hostname or "").lower()
    except ValueError:
        return "is not a valid URL"
    if parts.scheme != "https":
        return "must be an https URL"
    if host == "benefits.gov" or host.endswith(".benefits.gov"):
        return "benefits.gov is retired and not allowed"
    if not (host.endswith(".gov") or host in EXTRA_HOSTS):
        return f"host {host or '(none)'} is not on the official allowlist"
    return None


def _strings(obj, path=""):
    if isinstance(obj, str):
        yield path, obj
    elif isinstance(obj, dict):
        for key, val in obj.items():
            yield from _strings(key, path)
            yield from _strings(val, f"{path}.{key}" if path else str(key))
    elif isinstance(obj, list):
        for i, val in enumerate(obj):
            yield from _strings(val, f"{path}[{i}]")


def _load(path: Path, flag, kind):
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        flag(path.name, "file", f"cannot read: {exc}")
        return None
    if not isinstance(data, kind):
        flag(path.name, "file", f"top level must be a JSON {'array' if kind is list else 'object'}")
        return None
    return data


def _ignore(*_args):
    pass


def _keys(obj: dict, model, prefix: str, pid: str, flag) -> bool:
    want, got = list(model.model_fields), list(obj)
    for key in got:
        if key not in want:
            flag(pid, prefix + key, "extra key not in the schema")
    for key in want:
        if key not in obj:
            flag(pid, prefix + key, "missing key")
    if got != want and set(got) == set(want):
        flag(pid, prefix.rstrip(".") or "record", "keys are not in schema order")
    return got == want


def required_fields(rec: dict) -> list[str]:
    """Sidecar field keys that Appendix A5 requires for this record."""
    elig = rec["eligibility"]
    need = ["description", "eligibility.citizenship_required", "application_url"]
    need += [f"eligibility.{k}" for k in ("income_limit_pct_fpl", "age_min", "age_max") if elig.get(k) is not None]
    need += [f"eligibility.{k}" for k in ("requires_children", "requires_disability", "requires_pregnancy") if elig.get(k) is True]
    need += [k for k in ("estimated_monthly_value_usd", "processing_time_days") if rec.get(k) is not None]
    return need + (["documents_needed"] if rec.get("documents_needed") else [])


def _check_record(rec, pid: str, fname: str, flag):
    """Return the validated Program, or None when the record cannot be checked further."""
    for path, text in _strings(rec):
        if EM_DASH in text:
            flag(pid, path or "record", "contains an em dash")
    if not isinstance(rec, dict):
        flag(pid, "record", "must be a JSON object")
        return None
    ok = _keys(rec, Program, "", pid, flag)
    if isinstance(rec.get("eligibility"), dict):
        ok = _keys(rec["eligibility"], Eligibility, "eligibility.", pid, flag) and ok
    elif "eligibility" in rec:
        flag(pid, "eligibility", "must be an object")
        ok = False
    if not ok:
        return None
    try:
        m = Program.model_validate(rec)
    except ValidationError as exc:
        for err in exc.errors():
            flag(pid, ".".join(map(str, err["loc"])) or "record", err["msg"])
        return None
    if not re.fullmatch(r"[a-z][a-z0-9]*(_[a-z0-9]+)*", m.program_id):
        flag(pid, "program_id", "must be lowercase snake case")
    if SUFFIX.get(fname) and not m.program_id.endswith(SUFFIX[fname]):
        flag(pid, "program_id", f"must end in {SUFFIX[fname]} in {fname}")
    if m.category not in CATEGORIES:
        flag(pid, "category", f"{m.category!r} is not one of {sorted(CATEGORIES)}")
    try:
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", m.last_updated):
            raise ValueError
        if date.fromisoformat(m.last_updated) > date.today():
            flag(pid, "last_updated", "is in the future")
    except ValueError:
        flag(pid, "last_updated", "must be an ISO date, YYYY-MM-DD")
    if (msg := host_status(m.application_url)) is not None:
        flag(pid, "application_url", msg)
    e = m.eligibility
    for field, val, lo, hi in (
        ("eligibility.income_limit_pct_fpl", e.income_limit_pct_fpl, 1, 500),
        ("eligibility.age_min", e.age_min, 0, 120),
        ("eligibility.age_max", e.age_max, 0, 120),
        ("estimated_monthly_value_usd", m.estimated_monthly_value_usd, 0, None),
        ("processing_time_days", m.processing_time_days, 1, 730),
    ):
        if val is not None and (val < lo or (hi is not None and val > hi)):
            flag(pid, field, f"{val} is outside {lo} to {hi if hi is not None else 'no upper limit'}")
    if e.age_min is not None and e.age_max is not None and e.age_min > e.age_max:
        flag(pid, "eligibility.age_min", "is greater than age_max")
    words = len(m.description.split())
    if not 60 <= words <= 180:
        flag(pid, "description", f"{words} words, need 60 to 180")
    return m


def _check_sidecar(sidecar, sname: str, pid: str, rec: dict, model, flag, unconfirmed: list) -> None:
    entry = sidecar.get(pid) if sidecar else None
    fields = entry.get("fields") if isinstance(entry, dict) else None
    if not isinstance(fields, dict):
        flag(pid, "sidecar", f"no entry with a fields object in data/sources/{sname}")
        return
    for path, text in _strings(entry):
        if EM_DASH in text:
            flag(pid, f"sidecar.{path}", "contains an em dash")
    need = required_fields(rec) if model is not None else []
    for key in need:
        if key not in fields:
            flag(pid, key, "missing from sidecar")
    for key, f in fields.items():
        if not isinstance(f, dict):
            flag(pid, key, "sidecar field must be an object")
            continue
        urls = urls_of(f)
        if not urls or len(urls) != len(f.get("urls")):
            flag(pid, key, "sidecar needs a non-empty list of url strings")
        for url in urls:
            if (msg := host_status(url)) is not None:
                flag(pid, key, f"sidecar url {url}: {msg}")
        if f.get("unconfirmed") is True:
            if key in BOOL_FIELDS:
                unconfirmed.append((pid, key))
            else:
                flag(pid, key, "unconfirmed is allowed only on boolean eligibility fields")
        elif key in need and key not in NO_EVIDENCE and not str(f.get("evidence") or "").strip():
            flag(pid, key, "evidence is required")


def urls_of(field: dict) -> list[str]:
    urls = field.get("urls")
    return [u for u in urls if isinstance(u, str)] if isinstance(urls, list) else []


def validate(data_dir) -> tuple[int, list, list]:
    """Return (program count, problems, unconfirmed); problems are (program_id, field, message)."""
    data_dir = Path(data_dir)
    problems: list = []
    unconfirmed: list = []
    seen: dict = {}
    count = 0

    def flag(pid, field, msg):
        problems.append((pid, field, msg))

    for path in sorted((data_dir / "programs").glob("*.json")):
        sname = f"{path.stem.removesuffix('_programs')}_sources.json"
        sidecar_path = data_dir / "sources" / sname
        sidecar = _load(sidecar_path, flag, dict) if sidecar_path.exists() else None
        for i, rec in enumerate(_load(path, flag, list) or []):
            count += 1
            pid = rec.get("program_id") if isinstance(rec, dict) else None
            pid = pid if isinstance(pid, str) and pid else f"{path.name}[{i}]"
            if pid in seen:
                flag(pid, "program_id", f"duplicate, already defined in {seen[pid]}")
            seen.setdefault(pid, path.name)
            model = _check_record(rec, pid, path.name, flag)
            if isinstance(rec, dict):
                _check_sidecar(sidecar, sname, pid, rec, model, flag, unconfirmed)
    return count, problems, unconfirmed


def iter_sidecar_fields(data_dir):
    """Yield (program_id, field key, field dict) for every entry in data/sources/*_sources.json."""
    for path in sorted((Path(data_dir) / "sources").glob("*_sources.json")):
        for pid, entry in (_load(path, _ignore, dict) or {}).items():
            fields = entry.get("fields") if isinstance(entry, dict) else None
            for key, f in (fields.items() if isinstance(fields, dict) else []):
                if isinstance(f, dict):
                    yield pid, key, f


def _norm(text: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", text).translate(_QUOTES).split()).lower()


class _TextOnly(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        self.hidden += tag in ("script", "style")

    def handle_endtag(self, tag):
        self.hidden = max(0, self.hidden - (tag in ("script", "style")))

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


def snapshot_text(path: Path) -> str | None:
    """Normalized visible text of a saved HTML or PDF snapshot, or None when unreadable."""
    try:
        if path.suffix.lower() == ".pdf":
            from PyPDF2 import PdfReader

            return _norm(" ".join(page.extract_text() or "" for page in PdfReader(path).pages))
        parser = _TextOnly()
        parser.feed(path.read_bytes().decode("utf-8", "replace"))
        return _norm(" ".join(parser.parts))
    except Exception:  # unreadable or corrupt snapshot: report NO_SNAPSHOT
        return None


def check_evidence(data_dir) -> list[tuple]:
    """Rows of (FOUND|NOT_FOUND|NO_SNAPSHOT, program_id, field, url) from data/raw/fetch_log.json."""
    raw = Path(data_dir) / "raw"
    log = _load(raw / "fetch_log.json", _ignore, list) if (raw / "fetch_log.json").exists() else []
    snaps = {}
    for item in log or []:
        if isinstance(item, dict) and item.get("file"):
            snaps.update({item[k]: raw / item["file"] for k in ("url", "final_url") if item.get(k)})
    texts: dict = {}
    rows = []
    for pid, key, f in iter_sidecar_fields(data_dir):
        evidence = _norm(str(f.get("evidence") or ""))
        if not evidence or key == "application_url":  # its evidence is a fetch note, not page text
            continue
        for url in urls_of(f):
            path = snaps.get(url)
            if path not in texts:
                texts[path] = snapshot_text(path) if path else None
            text = texts[path]
            found = text is not None and (evidence in text or evidence.replace(" ", "") in text.replace(" ", ""))
            rows.append(("NO_SNAPSHOT" if text is None else "FOUND" if found else "NOT_FOUND", pid, key, url))
    return rows


def check_urls(data_dir, client: httpx.Client | None = None, delay: float = 1.0) -> list[tuple]:
    """Live GET of each application_url; rows of (status, program_id, url). Advisory only."""
    own = client is None
    client = client or httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=30.0, follow_redirects=True)
    rows: list = []
    for path in sorted((Path(data_dir) / "programs").glob("*.json")):
        for rec in _load(path, _ignore, list) or []:
            url = rec.get("application_url") if isinstance(rec, dict) else None
            if not isinstance(url, str):
                continue
            if host_status(url) is not None:
                status = "SKIPPED_NOT_ALLOWED"
            else:
                time.sleep(delay if rows else 0)
                try:
                    status = client.get(url).status_code
                except httpx.HTTPError as exc:
                    status = type(exc).__name__
            rows.append((status, str(rec.get("program_id")), url))
    if own:
        client.close()
    return rows


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Validate data/programs/*.json against the schema, conventions and sidecars.")
    ap.add_argument("--data-dir", type=Path, default=REPO_ROOT / "data", help="directory holding programs/, sources/, raw/")
    ap.add_argument("--check-evidence", action="store_true", help="look for sidecar evidence text in data/raw snapshots")
    ap.add_argument("--check-urls", action="store_true", help="live GET of each application_url")
    args = ap.parse_args(argv)
    count, problems, unconfirmed = validate(args.data_dir)
    for pid, field, msg in problems:
        print(f"PROBLEM {pid} {field}: {msg}")
    for pid, field in unconfirmed:
        print(f"UNCONFIRMED {pid} {field}")
    if args.check_evidence:
        for row in check_evidence(args.data_dir):
            print("EVIDENCE", *row)
    if args.check_urls:
        for status, pid, url in check_urls(args.data_dir):
            print(f"URL {status} {pid} {url}")
    print(f"SUMMARY programs={count} problems={len(problems)}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
