"""Standing gate: the real program records and their source sidecars must pass strict validation."""
import sys

from config import DATA_DIR

sys.path.insert(0, str(DATA_DIR / "scripts"))
import parse_programs as pp  # noqa: E402

REQUIRED_IDS = {
    "snap_federal", "medicaid_federal", "wic_federal", "liheap_federal",
    "medicare_extra_help_federal", "ssdi_federal",
    "chip_tx", "childrens_medicaid_tx", "medicaid_pregnant_women_tx", "chip_perinatal_tx",
    "emergency_medicaid_tx", "medicaid_elderly_disabled_tx", "tanf_tx", "unemployment_benefits_tx",
}


def test_validator_reports_zero_problems():
    count, problems, _unconfirmed = pp.validate(DATA_DIR)
    assert problems == []
    assert count == len(REQUIRED_IDS)


def test_required_program_ids_present():
    import json

    ids = set()
    for path in (DATA_DIR / "programs").glob("*_programs.json"):
        ids |= {r["program_id"] for r in json.loads(path.read_text(encoding="utf-8"))}
    assert REQUIRED_IDS <= ids


def test_every_programs_file_has_a_sources_file():
    for path in (DATA_DIR / "programs").glob("*_programs.json"):
        sidecar = DATA_DIR / "sources" / path.name.replace("_programs.json", "_sources.json")
        assert sidecar.exists(), f"missing {sidecar.name}"


def test_no_numeric_field_marked_unconfirmed():
    _count, _problems, unconfirmed = pp.validate(DATA_DIR)
    numeric = [u for u in unconfirmed if not str(u[1]).startswith("eligibility.") or "pct" in str(u[1]) or "age" in str(u[1])]
    assert numeric == []
    for pid, field, f in pp.iter_sidecar_fields(DATA_DIR):
        if f.get("unconfirmed"):
            assert field in pp.BOOL_FIELDS, f"{pid} {field} unconfirmed but not a boolean field"
