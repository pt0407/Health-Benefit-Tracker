"""Unit tests for data/scripts/parse_programs.py and scrape_benefits_data.py.

Everything runs on tmp_path fixtures with synthetic programs; no real figures, no network.
"""
import hashlib
import json
import sys

import httpx
import pytest

from config import DATA_DIR

sys.path.insert(0, str(DATA_DIR / "scripts"))
import parse_programs as pp  # noqa: E402
import scrape_benefits_data as sb  # noqa: E402

FED, TX = "example_food_help_federal", "example_clinic_help_tx"
OK_URL = "https://www.example.gov/ok"
BLOCKED_URL = "https://www.example.gov/blocked"
MISSING_URL = "https://www.example.gov/missing"
DESC = "Example Food Help is a made up program used only in tests. " + " ".join(["filler"] * 60)


def record(pid, **over):
    rec = {
        "program_id": pid, "name": "Example Food Help", "type": "federal", "category": "nutrition",
        "description": DESC,
        "eligibility": {
            "income_limit_pct_fpl": 130, "citizenship_required": False, "age_min": None, "age_max": 18,
            "requires_children": False, "requires_disability": False, "requires_pregnancy": False,
        },
        "estimated_monthly_value_usd": 100.0, "application_url": "https://www.example.gov/apply",
        "documents_needed": ["Example ID"], "processing_time_days": 30, "source": "Example Agency",
        "last_updated": "2020-01-01",
    }
    rec.update(over)
    return rec


def sidecar(rec):
    fields = {
        key: {"urls": [OK_URL], "evidence": "" if key in pp.NO_EVIDENCE else "example snippet", "note": ""}
        for key in pp.required_fields(rec)
    }
    return {rec["program_id"]: {"verified_on": "2020-01-01", "figures_effective": "example period", "fields": fields}}


def build(tmp_path, mutate=None):
    """Write a valid two-program data dir (after an optional edit of the in-memory state)."""
    fed, tx = record(FED), record(TX, type="state")
    state = {
        "federal_programs": [fed], "texas_programs": [tx],
        "federal_sources": sidecar(fed), "texas_sources": sidecar(tx),
    }
    if mutate:
        mutate(state)
    for name, content in state.items():
        folder = tmp_path / ("sources" if name.endswith("_sources") else "programs")
        folder.mkdir(parents=True, exist_ok=True)
        (folder / f"{name}.json").write_text(json.dumps(content, indent=2), encoding="utf-8")
    return tmp_path


def fed(s):
    return s["federal_programs"][0]


def fields(s):
    return s["federal_sources"][FED]["fields"]


CASES = [
    ("missing_sidecar_key", lambda s: fields(s).pop("eligibility.citizenship_required"), "eligibility.citizenship_required", "missing from sidecar"),
    ("no_sidecar_entry", lambda s: s["federal_sources"].clear(), "sidecar", "no entry"),
    ("benefits_gov_url", lambda s: fed(s).update(application_url="https://www.benefits.gov/benefit/1"), "application_url", "benefits.gov"),
    ("http_url", lambda s: fed(s).update(application_url="http://www.example.gov/apply"), "application_url", "https"),
    ("host_not_allowlisted", lambda s: fed(s).update(application_url="https://example.com/apply"), "application_url", "allowlist"),
    ("sidecar_host_not_allowlisted", lambda s: fields(s)["description"].update(urls=["https://example.com/x"]), "description", "allowlist"),
    ("duplicate_id", lambda s: s["texas_programs"][0].update(program_id=FED), "program_id", "duplicate"),
    ("wrong_suffix", lambda s: s["texas_programs"][0].update(program_id="example_clinic_help_federal"), "program_id", "must end in _tx"),
    ("not_snake_case", lambda s: fed(s).update(program_id="Example-Food_federal"), "program_id", "snake case"),
    ("extra_key", lambda s: fed(s).update(bonus=1), "bonus", "extra key"),
    ("missing_eligibility_key", lambda s: fed(s)["eligibility"].pop("requires_pregnancy"), "eligibility.requires_pregnancy", "missing key"),
    ("key_order", lambda s: s.update(federal_programs=[dict(reversed(list(fed(s).items())))]), "record", "schema order"),
    ("wrong_type", lambda s: fed(s).update(processing_time_days="soon"), "processing_time_days", "valid integer"),
    ("numeric_without_evidence", lambda s: fields(s)["eligibility.income_limit_pct_fpl"].update(evidence=""), "eligibility.income_limit_pct_fpl", "evidence is required"),
    ("unconfirmed_on_numeric", lambda s: fields(s)["eligibility.income_limit_pct_fpl"].update(unconfirmed=True), "eligibility.income_limit_pct_fpl", "only on boolean"),
    ("em_dash", lambda s: fed(s).update(name="Example" + chr(0x2014) + "Help"), "name", "em dash"),
    ("bad_category", lambda s: fed(s).update(category="food"), "category", "not one of"),
    ("future_date", lambda s: fed(s).update(last_updated="2999-01-01"), "last_updated", "future"),
    ("not_iso_date", lambda s: fed(s).update(last_updated="01/02/2020"), "last_updated", "ISO date"),
    ("short_description", lambda s: fed(s).update(description="Too short."), "description", "need 60 to 180"),
    ("percent_out_of_range", lambda s: fed(s)["eligibility"].update(income_limit_pct_fpl=900), "eligibility.income_limit_pct_fpl", "outside"),
    ("age_out_of_range", lambda s: fed(s)["eligibility"].update(age_max=150), "eligibility.age_max", "outside"),
    ("age_min_above_max", lambda s: fed(s)["eligibility"].update(age_min=30), "eligibility.age_min", "greater than age_max"),
    ("negative_value", lambda s: fed(s).update(estimated_monthly_value_usd=-1), "estimated_monthly_value_usd", "outside"),
    ("zero_processing_days", lambda s: fed(s).update(processing_time_days=0), "processing_time_days", "outside"),
]


VALUE = "estimated_monthly_value_usd"
INCOME = "eligibility.income_limit_pct_fpl"


def marker(**over):
    """A valid estimate marker for the sample value of 100: round(annual / 12) with annual = 1200."""
    est = {
        "method": "per_enrollee_spending",
        "represents": "Example government spending per enrollee, not cash paid to the household.",
        "formula": "round(annual / 12)",
        "inputs": [{"name": "annual", "value": 1200, "unit": "USD per year", "period": "example year",
                    "url": OK_URL, "evidence": "example spending was 1200 dollars"}],
    }
    est.update(over)
    return {"estimated": True, "estimate": est}


def estimated(**over):
    def edit(s):
        fed(s)["description"] += " This is an estimate."
        fields(s)[VALUE].update(marker(**over))
    return edit


def edit_input(**over):
    def edit(s):
        estimated()(s)
        fields(s)[VALUE]["estimate"]["inputs"][0].update(over)
    return edit


def drop(*keys, field=VALUE):
    def edit(s):
        estimated()(s)
        for k in keys:
            fields(s)[field]["estimate"].pop(k)
    return edit


def null_value(s):
    fed(s)[VALUE] = None


def formula_case(formula, inputs=None):
    def edit(s):
        estimated(formula=formula)(s)
        if inputs is not None:
            fields(s)[VALUE]["estimate"]["inputs"] = inputs
    return edit


def number(name, value=1200):
    return {"name": name, "value": value, "unit": "USD", "period": "example", "url": OK_URL, "evidence": "example"}


MARKER_CASES = [
    ("missing_formula", drop("formula"), VALUE, "formula is missing"),
    ("missing_inputs", drop("inputs"), VALUE, "inputs must be a non-empty list"),
    ("missing_represents", drop("represents"), VALUE, "represents"),
    ("formula_result_differs", estimated(formula="round(annual / 10)"), VALUE, "gives 120 but the record value is 100"),
    ("unknown_name", estimated(formula="round(yearly / 12)"), VALUE, "'yearly'"),
    ("unused_input", formula_case("round(annual / 12)", [number("annual"), number("extra", 5)]), VALUE, "'extra' is not used"),
    ("attribute_access", estimated(formula="annual.real / 12"), VALUE, "Attribute"),
    ("other_function_call", estimated(formula="abs(annual) / 12"), VALUE, "may only call"),
    ("dunder_call", estimated(formula="__import__('os').getcwd()"), VALUE, "may only call"),
    ("power_operator", estimated(formula="annual ** 2"), VALUE, "Pow"),
    ("string_constant", estimated(formula="'a' + annual"), VALUE, "Constant"),
    ("syntax_error", estimated(formula="annual /"), VALUE, "valid arithmetic"),
    ("division_by_zero", estimated(formula="annual / 0"), VALUE, "cannot be evaluated"),
    ("bad_method", estimated(method="guess"), VALUE, "method must be one of"),
    ("input_url_off_allowlist", edit_input(url="https://example.com/x"), VALUE, "allowlist"),
    ("input_url_not_in_entry_urls", edit_input(url="https://www.example.gov/other"), VALUE, "not listed in this entry's urls"),
    ("input_evidence_too_long", edit_input(evidence=" ".join(["word"] * 16)), VALUE, "need 1 to 15"),
    ("input_evidence_empty", edit_input(evidence=""), VALUE, "need 1 to 15"),
    ("input_value_not_number", edit_input(value="1200"), VALUE, "value must be a number"),
    ("input_name_not_identifier", edit_input(name="annual spend"), VALUE, "identifier"),
    ("input_name_is_function", edit_input(name="round"), VALUE, "identifier"),
    ("duplicate_input_name", formula_case("annual / 12", [number("annual"), number("annual")]), VALUE, "used twice"),
    ("estimated_on_boolean_field", lambda s: fields(s)["eligibility.citizenship_required"].update(marker()), "eligibility.citizenship_required", "allowed only on"),
    ("estimate_without_estimated", lambda s: fields(s)[VALUE].update(estimate=marker()["estimate"]), VALUE, "without estimated: true"),
    ("estimated_false_with_estimate", lambda s: fields(s)[VALUE].update(estimated=False, estimate=marker()["estimate"]), VALUE, "without estimated: true"),
    ("estimated_without_estimate", lambda s: fields(s)[VALUE].update(estimated=True), VALUE, "estimate is missing"),
    ("estimated_not_boolean", lambda s: fields(s)[VALUE].update(estimated="yes"), VALUE, "true or false"),
    ("estimated_on_null_value", lambda s: (null_value(s), estimated()(s)), VALUE, "record value is null"),
    ("estimated_without_evidence", lambda s: (estimated()(s), fields(s)[VALUE].update(evidence="")), VALUE, "evidence is required"),
    ("description_lacks_estimate", lambda s: (estimated()(s), fed(s).update(description=DESC)), "description", "must contain the word 'estimate'"),
    ("null_without_sidecar_entry", null_value, VALUE, "null_reason"),
    ("null_entry_without_null_reason", lambda s: (null_value(s), fields(s).update({VALUE: {"urls": [OK_URL], "evidence": "", "note": "why"}})), VALUE, "null_reason"),
    ("null_entry_bad_code", lambda s: (null_value(s), fields(s).update({VALUE: {"urls": [OK_URL], "evidence": "", "note": "why", "null_reason": "unknown"}})), VALUE, "null_reason must be one of"),
    ("null_entry_without_note", lambda s: (null_value(s), fields(s).update({VALUE: {"urls": [OK_URL], "evidence": "", "null_reason": "not_applicable"}})), VALUE, "needs a note"),
    ("no_income_test_on_other_field", lambda s: (null_value(s), fields(s).update({VALUE: {"urls": [OK_URL], "evidence": "", "note": "why", "null_reason": "no_income_test"}})), VALUE, "null_reason"),
    ("null_reason_on_non_null_field", lambda s: fields(s)[VALUE].update(null_reason="not_applicable"), VALUE, "only allowed when the record value is null"),
    ("income_value_zero", lambda s: fed(s)["eligibility"].update(income_limit_pct_fpl=0), INCOME, "outside"),
]


@pytest.mark.parametrize("mutate,field,fragment", [c[1:] for c in MARKER_CASES], ids=[c[0] for c in MARKER_CASES])
def test_marker_rule_is_caught(tmp_path, mutate, field, fragment):
    _, problems, _ = pp.validate(build(tmp_path, mutate))
    assert any(f == field and fragment in msg for _, f, msg in problems), problems


def null_entry(code):
    return {"urls": [OK_URL], "evidence": "", "note": "example reason", "null_reason": code}


def test_valid_marker_passes_and_is_listed(tmp_path):
    data = build(tmp_path, estimated())
    assert pp.validate(data) == (2, [], [])
    assert pp.estimated_fields(data) == [(FED, VALUE, "per_enrollee_spending")]


def test_valid_markers_on_all_three_numeric_fields_pass(tmp_path):
    def edit(s):
        estimated()(s)
        fed(s)["eligibility"]["income_limit_pct_fpl"] = 75
        fed(s)["processing_time_days"] = 21
        fields(s)[INCOME].update(marker(method="dollar_limit_to_pct_fpl", formula="floor(monthly * 12 / guideline * 100)", inputs=[
            {**number("monthly", 1500), "evidence": "limit is 1500 a month"}, {**number("guideline", 24000), "evidence": "example guideline"}]))
        fields(s)["processing_time_days"].update(marker(method="unit_conversion", formula="weeks * 7", inputs=[number("weeks", 3)]))
    data = build(tmp_path, edit)
    assert pp.validate(data) == (2, [], [])
    assert [m for _, _, m in pp.estimated_fields(data)] == ["dollar_limit_to_pct_fpl", "per_enrollee_spending", "unit_conversion"]


def test_null_reason_entries_pass_for_each_code(tmp_path):
    def edit(s):
        fed(s)["eligibility"]["income_limit_pct_fpl"] = None
        fed(s)[VALUE] = None
        fed(s)["processing_time_days"] = None
        fields(s).update({INCOME: null_entry("no_income_test"), VALUE: null_entry("no_official_basis"),
                          "processing_time_days": null_entry("not_applicable")})
    assert pp.validate(build(tmp_path, edit)) == (2, [], [])


@pytest.mark.parametrize("formula,inputs,expected", [
    ("-a + b * (c - 1) / 2", {"a": 4, "b": 3, "c": 5}, 2.0),
    ("round(a / 3)", {"a": 10}, 3),
    ("floor(a / 3) + ceil(a / 3)", {"a": 10}, 7),
    ("min(a, b) + max(a, b)", {"a": 2, "b": 9}, 11),
    ("(a + 1.5) * 2", {"a": 1}, 5.0),
])
def test_formula_evaluator_accepts_whitelisted_arithmetic(formula, inputs, expected):
    result, used = pp.evaluate_formula(formula, inputs)
    assert result == expected and used <= set(inputs)


def test_cli_prints_estimate_lines_and_keeps_summary_last(tmp_path, capsys):
    assert pp.main(["--data-dir", str(build(tmp_path, estimated()))]) == 0
    lines = capsys.readouterr().out.splitlines()
    assert lines == [f"ESTIMATE {FED} {VALUE} per_enrollee_spending 100", "SUMMARY programs=2 problems=0"]


def test_valid_sample_passes(tmp_path):
    assert pp.validate(build(tmp_path)) == (2, [], [])


@pytest.mark.parametrize("mutate,field,fragment", [c[1:] for c in CASES], ids=[c[0] for c in CASES])
def test_rule_is_caught(tmp_path, mutate, field, fragment):
    _, problems, _ = pp.validate(build(tmp_path, mutate))
    assert any(f == field and fragment in msg for _, f, msg in problems), problems


@pytest.mark.parametrize("url,allowed", [
    ("https://www.example.gov/x", True), ("https://sub.example.texas.gov/x", True),
    ("https://www.yourtexasbenefits.com/", True), ("https://texaswic.org/", True),
    ("https://www.benefits.gov/benefit/1", False), ("https://api.benefits.gov/", False),
    ("http://www.example.gov/", False), ("https://example.com/", False),
    ("https://www.example.gov.evil.com/", False), ("https://evilgov.com/", False),
])
def test_host_allowlist(url, allowed):
    assert (pp.host_status(url) is None) is allowed


def test_unconfirmed_boolean_is_allowed_and_listed(tmp_path):
    def edit(s):
        fields(s)["eligibility.citizenship_required"].update(unconfirmed=True, evidence="")
    _, problems, unconfirmed = pp.validate(build(tmp_path, edit))
    assert problems == [] and unconfirmed == [(FED, "eligibility.citizenship_required")]


def test_cli_prints_summary_last_and_sets_exit_code(tmp_path, capsys):
    assert pp.main(["--data-dir", str(build(tmp_path / "ok"))]) == 0
    assert capsys.readouterr().out.splitlines()[-1] == "SUMMARY programs=2 problems=0"
    assert pp.main(["--data-dir", str(build(tmp_path / "bad", lambda s: fed(s).update(category="food")))]) == 1
    lines = capsys.readouterr().out.splitlines()
    assert lines[0].startswith(f"PROBLEM {FED} category: ") and lines[-1] == "SUMMARY programs=2 problems=1"


def fake_snapshot(data_dir):
    raw = data_dir / "raw"
    raw.mkdir()
    (raw / "page.html").write_text(
        "<html><script>var hidden = 'secret words';</script><body><p>Example   Food Help: the income limit is "
        "<b>130</b> percent of the example guideline.</p></body></html>", encoding="utf-8")
    log = [{"url": OK_URL, "final_url": OK_URL, "status": 200, "file": "page.html"}, {"url": BLOCKED_URL, "status": 403}]
    (raw / "fetch_log.json").write_text(json.dumps(log), encoding="utf-8")


def test_evidence_check_reports_found_not_found_and_no_snapshot(tmp_path):
    def edit(s):
        f = fields(s)
        f["eligibility.income_limit_pct_fpl"].update(urls=[OK_URL], evidence="INCOME  limit is 130 percent")
        f["eligibility.age_max"].update(urls=[OK_URL], evidence="up to age 99")
        f["processing_time_days"].update(urls=[OK_URL], evidence="secret words")  # only inside a script tag
        f["estimated_monthly_value_usd"].update(urls=[BLOCKED_URL], evidence="about $100")
    data = build(tmp_path, edit)
    fake_snapshot(data)
    rows = {(pid, key): status for status, pid, key, _url in pp.check_evidence(data)}
    assert rows[(FED, "eligibility.income_limit_pct_fpl")] == "FOUND"
    assert rows[(FED, "eligibility.age_max")] == "NOT_FOUND"
    assert rows[(FED, "processing_time_days")] == "NOT_FOUND"
    assert rows[(FED, "estimated_monthly_value_usd")] == "NO_SNAPSHOT"
    assert (FED, "application_url") not in rows


def test_check_urls_uses_honest_user_agent_and_skips_disallowed_hosts(tmp_path):
    seen = []

    def handler(request):
        seen.append(request.headers["user-agent"])
        return httpx.Response(200)

    data = build(tmp_path, lambda s: s["texas_programs"][0].update(application_url="https://www.benefits.gov/x"))
    rows = pp.check_urls(data, client=sb.make_client(httpx.MockTransport(handler)), delay=0)
    assert rows == [(200, FED, "https://www.example.gov/apply"), ("SKIPPED_NOT_ALLOWED", TX, "https://www.benefits.gov/x")]
    assert seen == [pp.USER_AGENT] and "BenefitsFinder-data-snapshot" in seen[0]


def test_scraper_logs_each_url_once_and_marks_403_blocked(tmp_path, capsys):
    def edit(s):
        f = fields(s)
        f["eligibility.age_max"]["urls"] = [BLOCKED_URL]
        f["estimated_monthly_value_usd"]["urls"] = [MISSING_URL]
        f["processing_time_days"]["urls"] = ["https://example.com/not-official"]
    data = build(tmp_path, edit)
    calls = []

    def handler(request):
        calls.append(str(request.url))
        assert request.headers["user-agent"] == pp.USER_AGENT
        return {OK_URL: httpx.Response(200, html="<p>ok page</p>"), BLOCKED_URL: httpx.Response(403),
                MISSING_URL: httpx.Response(404)}[str(request.url)]

    counts = sb.snapshot(data, client=sb.make_client(httpx.MockTransport(handler)), delay=0)
    assert counts == {"urls": 4, "ok": 1, "blocked": 1, "error": 2}
    assert sorted(calls) == sorted([OK_URL, BLOCKED_URL, MISSING_URL])  # OK_URL once, official hosts only
    lines = capsys.readouterr().out.splitlines()
    assert f"FETCH BLOCKED 403 {BLOCKED_URL}" in lines and f"FETCH OK 200 {OK_URL}" in lines
    assert f"FETCH ERROR http-404 {MISSING_URL}" in lines
    assert "FETCH ERROR host-not-allowed https://example.com/not-official" in lines
    assert lines[-1] == "SUMMARY urls=4 ok=1 blocked=1 error=2"
    log = {e["url"]: e for e in json.loads((data / "raw" / "fetch_log.json").read_text(encoding="utf-8"))}
    assert log[BLOCKED_URL]["status"] == 403 and "file" not in log[BLOCKED_URL]
    ok = log[OK_URL]
    body = (data / "raw" / ok["file"]).read_bytes()
    assert ok["sha256"] == hashlib.sha256(body).hexdigest() and ok["bytes"] == len(body) and ok["final_url"] == OK_URL


def test_scraper_retries_a_server_error_once(tmp_path):
    answers = iter([httpx.Response(503), httpx.Response(200, html="<p>second try</p>")])
    client = sb.make_client(httpx.MockTransport(lambda request: next(answers)))
    entry = sb.fetch_one(client, OK_URL, tmp_path, delay=0)
    assert entry["status"] == 200 and "file" in entry


def test_scraper_exit_codes(tmp_path):
    assert sb.main(["--data-dir", str(tmp_path)]) == 0  # nothing listed
    assert (tmp_path / "raw" / "fetch_log.json").read_text(encoding="utf-8").strip() == "[]"
