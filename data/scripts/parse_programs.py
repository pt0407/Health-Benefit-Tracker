#!/usr/bin/env python3
"""Validate the hand-curated benefit records in data/programs/*.json.

The records are written by people from official agency pages. This script does not generate
them: it checks each record against models.program.Program, the data conventions in
data/scripts/README.md, and the per-field sources in data/sources/<name>_sources.json.

Output lines:
  PROBLEM <program_id> <field>: <message>
  UNCONFIRMED <program_id> <field>                                       (allowed, listed)
  ESTIMATE <program_id> <field> <method> <value>                         (advisory: value is estimated or derived)
  EVIDENCE <FOUND|NOT_FOUND|NO_SNAPSHOT> <program_id> <field> <url>      (--check-evidence)
  URL <status> <program_id> <url>                                        (--check-urls)
  SUMMARY programs=<n> problems=<n>
Exit status is 1 only when problems > 0; the EVIDENCE and URL lines are advisory.
"""
from __future__ import annotations

import argparse
import ast
import json
import math
import operator
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
NUMERIC_FIELDS = ("eligibility.income_limit_pct_fpl", "estimated_monthly_value_usd", "processing_time_days")
ESTIMATE_METHODS = {
    "dollar_limit_to_pct_fpl", "per_enrollee_spending", "official_average", "range_midpoint", "unit_conversion", "official_basis",
}
NULL_REASONS = {"no_income_test", "not_applicable", "no_official_basis"}
FORMULA_FUNCS = {"round": round, "floor": math.floor, "ceil": math.ceil, "min": min, "max": max}
_BINOPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv}
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


def evaluate_formula(formula: str, values: dict) -> tuple[float, set]:
    """Evaluate an estimate formula without eval(); return (result, names used).

    Allowed: numbers, input names, + - * /, unary minus, parentheses, and calls to round, floor,
    ceil, min, max. Anything else raises ValueError.
    """
    if len(formula) > 500:
        raise ValueError("is longer than 500 characters")
    try:
        tree = ast.parse(formula.strip(), mode="eval")
    except (SyntaxError, ValueError, RecursionError):
        raise ValueError("is not a valid arithmetic expression") from None
    used: set = set()

    def walk(node):
        if isinstance(node, ast.Expression):
            return walk(node.body)
        if isinstance(node, ast.Constant) and type(node.value) in (int, float):
            return node.value
        if isinstance(node, ast.Name):
            if node.id not in values:
                raise ValueError(f"uses {node.id!r}, which is not an input name")
            used.add(node.id)
            return values[node.id]
        if isinstance(node, ast.BinOp) and type(node.op) in _BINOPS:
            return _BINOPS[type(node.op)](walk(node.left), walk(node.right))
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
            return -walk(node.operand)
        if isinstance(node, ast.Call):
            if not (isinstance(node.func, ast.Name) and node.func.id in FORMULA_FUNCS) or node.keywords:
                raise ValueError(f"may only call {', '.join(FORMULA_FUNCS)} with positional arguments")
            return FORMULA_FUNCS[node.func.id](*[walk(a) for a in node.args])
        op = getattr(node, "op", None)
        raise ValueError(f"contains {type(op or node).__name__}, which is not allowed")

    try:
        result = walk(tree)
    except RecursionError:
        raise ValueError("is nested too deeply") from None
    except (ArithmeticError, TypeError) as exc:
        raise ValueError(f"cannot be evaluated ({type(exc).__name__}: {exc})") from None
    if isinstance(result, bool) or not isinstance(result, (int, float)) or math.isnan(result):
        raise ValueError("did not produce a number")
    return result, used


def _record_value(rec: dict, key: str):
    src = rec.get("eligibility") if key.startswith("eligibility.") else rec
    return src.get(key.split(".")[-1]) if isinstance(src, dict) else None


def _is_number(val) -> bool:
    return isinstance(val, (int, float)) and not isinstance(val, bool)


def _text(val) -> str:
    return val.strip() if isinstance(val, str) else ""


def _check_estimate(pid: str, key: str, f: dict, value, flag) -> None:
    est = f.get("estimate")
    if not isinstance(est, dict):
        flag(pid, key, "estimated is true but estimate is missing or not an object")
        return
    if est.get("method") not in ESTIMATE_METHODS:
        flag(pid, key, f"estimate.method must be one of {sorted(ESTIMATE_METHODS)}")
    if not _text(est.get("represents")):
        flag(pid, key, "estimate.represents must be a non-empty sentence")
    formula = _text(est.get("formula"))
    if not formula:
        flag(pid, key, "estimate.formula is missing")
    inputs, values, inputs_ok = est.get("inputs"), {}, True
    if not isinstance(inputs, list) or not inputs:
        flag(pid, key, "estimate.inputs must be a non-empty list")
        return
    listed = urls_of(f)
    for i, item in enumerate(inputs):
        where = f"estimate.inputs[{i}]"
        if not isinstance(item, dict):
            flag(pid, key, f"{where} must be an object")
            inputs_ok = False
            continue
        name = item.get("name")
        if not (isinstance(name, str) and name.isidentifier()) or name in FORMULA_FUNCS:
            flag(pid, key, f"{where}.name must be an identifier that is not a formula function")
            inputs_ok = False
        elif name in values:
            flag(pid, key, f"{where}.name {name!r} is used twice")
            inputs_ok = False
        elif _is_number(item.get("value")):
            values[name] = item["value"]
        if not _is_number(item.get("value")):
            flag(pid, key, f"{where}.value must be a number")
            inputs_ok = False
        for part in ("unit", "period"):
            if not _text(item.get(part)):
                flag(pid, key, f"{where}.{part} must be non-empty text")
        url = item.get("url")
        if not isinstance(url, str) or (msg := host_status(url)) is not None:
            flag(pid, key, f"{where}.url: {msg if isinstance(url, str) else 'must be a URL string'}")
        elif url not in listed:
            flag(pid, key, f"{where}.url is not listed in this entry's urls")
        words = len(_text(item.get("evidence")).split())
        if not 1 <= words <= 15:
            flag(pid, key, f"{where}.evidence has {words} words, need 1 to 15")
    if not formula or not inputs_ok:
        return
    try:
        result, used = evaluate_formula(formula, values)
    except ValueError as exc:
        flag(pid, key, f"estimate.formula {exc}")
        return
    for name in sorted(set(values) - used):
        flag(pid, key, f"estimate input {name!r} is not used in the formula")
    if _is_number(value) and abs(result - value) > 0.005:
        flag(pid, key, f"estimate.formula gives {result:g} but the record value is {value:g}")


def _check_marker(pid: str, key: str, f: dict, rec: dict, flag) -> bool:
    """Check the estimate and null_reason markers on one sidecar field; True when it is estimated."""
    numeric = key in NUMERIC_FIELDS
    value = _record_value(rec, key) if numeric else None
    est = f.get("estimated")
    if "estimated" in f and not isinstance(est, bool):
        flag(pid, key, "estimated must be true or false")
    if (est is True or "estimate" in f) and not numeric:
        flag(pid, key, f"estimated and estimate are allowed only on {', '.join(NUMERIC_FIELDS)}")
    elif est is True:
        if value is None:
            flag(pid, key, "estimated is true but the record value is null")
        _check_estimate(pid, key, f, value, flag)
    elif "estimate" in f:
        flag(pid, key, "estimate is present without estimated: true")
    if "null_reason" in f:
        if f["null_reason"] not in NULL_REASONS:
            flag(pid, key, f"null_reason must be one of {sorted(NULL_REASONS)}")
        if numeric and value is not None:
            flag(pid, key, "null_reason is only allowed when the record value is null")
    return numeric and est is True


def _check_null_reasons(pid: str, rec: dict, fields: dict, flag) -> None:
    for key in NUMERIC_FIELDS:
        if _record_value(rec, key) is not None:
            continue
        f = fields.get(key)
        reason = f.get("null_reason") if isinstance(f, dict) else None
        allowed = NULL_REASONS if key == NUMERIC_FIELDS[0] else NULL_REASONS - {"no_income_test"}
        if reason not in allowed:
            flag(pid, key, f"null value needs a sidecar entry with null_reason, one of {sorted(allowed)}")
        elif not _text(f.get("note")):
            flag(pid, key, "null_reason entry needs a note giving the exact reason")


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
    estimated = False
    for key in need:
        if key not in fields:
            flag(pid, key, "missing from sidecar")
    for key, f in fields.items():
        if not isinstance(f, dict):
            flag(pid, key, "sidecar field must be an object")
            continue
        urls = urls_of(f)
        estimated = _check_marker(pid, key, f, rec, flag) or estimated
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
    if model is not None:
        _check_null_reasons(pid, rec, fields, flag)
        if estimated and "estimate" not in str(rec.get("description", "")).lower():
            flag(pid, "description", "a field is estimated, so the description must contain the word 'estimate'")


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


def _fmt(val) -> str:
    return str(int(val)) if isinstance(val, float) and val.is_integer() else str(val)


def _estimates(data_dir) -> list[tuple[str, str, str, object]]:
    values = {}
    for path in sorted((Path(data_dir) / "programs").glob("*.json")):
        for rec in _load(path, _ignore, list) or []:
            if isinstance(rec, dict) and isinstance(rec.get("program_id"), str):
                values[rec["program_id"]] = rec
    rows = []
    for pid, key, f in iter_sidecar_fields(data_dir):
        if f.get("estimated") is True:
            est = f.get("estimate")
            method = est.get("method") if isinstance(est, dict) else None
            rows.append((pid, key, method if isinstance(method, str) else "", _record_value(values.get(pid, {}), key)))
    return rows


def estimated_fields(data_dir) -> list[tuple[str, str, str]]:
    """(program_id, field, method) for every sidecar field marked estimated: true."""
    return [row[:3] for row in _estimates(data_dir)]


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
    for pid, field, method, value in _estimates(args.data_dir):
        print(f"ESTIMATE {pid} {field} {method} {_fmt(value)}")
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
