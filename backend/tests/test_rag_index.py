import importlib.util
import json
import re
import subprocess
import sys

import pytest

from rag.chunker import MAX_BODY_WORDS, OVERLAP_WORDS, chunk_program, chunk_programs, state_for
from rag.store import ChunkStore, load_programs
from tests.rag_fixtures import (
    FIXTURE_PROGRAMS, INDEX_SCRIPT, HashEmbedding, default_embedding_or_skip, write_programs_dir,
)

BY_ID = {p.program_id: p for p in FIXTURE_PROGRAMS}
METADATA_KEYS = {
    "program_id", "program_name", "type", "category", "state", "source", "section",
    "chunk_index", "requires_children", "requires_disability", "requires_pregnancy",
}


def body_of(chunk) -> str:
    return "\n".join(chunk.text.split("\n")[2:-1])


def chunk_for(program_id: str, section: str):
    return next(c for c in chunk_program(BY_ID[program_id]) if c.metadata["section"] == section)


def load_script():
    spec = importlib.util.spec_from_file_location("index_to_chromadb", INDEX_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_chunk_header_and_footer_format():
    program = BY_ID["example_food_help_federal"]
    lines = chunk_for(program.program_id, "overview").text.split("\n")
    assert lines[0] == "Program: Example Food Help [example_food_help_federal]"
    assert lines[1] == ("Type: federal | Category: nutrition | Source: Example Agency "
                        "| Last updated: 2026-01-01")
    assert lines[2] == program.description
    assert lines[-1] == "Apply: https://example.org/apply/food"
    for chunk in chunk_programs(FIXTURE_PROGRAMS):
        assert chunk.text.startswith("Program: ") and chunk.text.split("\n")[-1].startswith("Apply: ")


def test_bodies_are_capped_at_300_words_with_sentence_overlap():
    sentences = [f"Sentence number {i} has exactly seven words." for i in range(100)]
    long_program = BY_ID["example_food_help_federal"].model_copy(update={"description": " ".join(sentences)})
    chunks = [c for c in chunk_program(long_program) if c.metadata["section"] == "overview"]
    assert len(chunks) > 1
    bodies = [body_of(c) for c in chunks]
    assert all(len(b.split()) <= MAX_BODY_WORDS for b in bodies)
    for earlier, later in zip(bodies, bodies[1:]):
        shared = [s for s in sentences if s in earlier and s in later]
        assert shared and len(" ".join(shared).split()) <= OVERLAP_WORDS
        assert later.startswith(shared[0])
    assert all(any(s in b for b in bodies) for s in sentences)
    assert [c.id for c in chunks] == [f"example_food_help_federal:overview:{n}" for n in range(len(chunks))]


def test_overlong_sentence_is_still_capped():
    giant = " ".join(f"w{i}" for i in range(700)) + "."
    program = BY_ID["example_food_help_federal"].model_copy(update={"description": giant})
    bodies = [body_of(c) for c in chunk_program(program) if c.metadata["section"] == "overview"]
    assert len(bodies) > 1 and all(len(b.split()) <= MAX_BODY_WORDS for b in bodies)


def test_chunk_ids_are_deterministic_and_unique():
    first = [c.id for c in chunk_programs(FIXTURE_PROGRAMS)]
    assert first == [c.id for c in chunk_programs(list(FIXTURE_PROGRAMS))]
    assert len(first) == len(set(first))
    assert all(re.fullmatch(r"[a-z_]+:(overview|eligibility|apply):\d+", i) for i in first)
    with pytest.raises(ValueError, match="duplicate"):
        chunk_programs([FIXTURE_PROGRAMS[0], FIXTURE_PROGRAMS[0]])


def test_metadata_keys_values_and_state_rule():
    for chunk in chunk_programs(FIXTURE_PROGRAMS):
        meta = chunk.metadata
        assert set(meta) == METADATA_KEYS
        assert all(isinstance(v, (str, int, float, bool)) for v in meta.values())
        assert meta["state"] == ("TX" if meta["program_id"].endswith("_tx") else "US")
        assert chunk.id == f"{meta['program_id']}:{meta['section']}:{meta['chunk_index']}"
    kids = chunk_for("example_kids_health_plan_tx", "eligibility").metadata
    assert kids["state"] == "TX" and kids["requires_children"] is True and kids["requires_pregnancy"] is False
    assert state_for("snap_federal") == "US" and state_for("chip_tx") == "TX"
    assert chunk_for("example_disability_income_federal", "apply").metadata["requires_disability"] is True


def test_eligibility_text_restates_fields_and_omits_false_flags():
    food = chunk_for("example_food_help_federal", "eligibility").text
    assert "Income limit: up to 130 percent of the federal poverty level." in food
    for absent in ("Requires", "Citizenship", "Age:", "no ", "not required"):
        assert absent not in body_of(chunk_for("example_food_help_federal", "eligibility"))
    senior = body_of(chunk_for("example_senior_drug_help_federal", "eligibility"))
    assert "the person who receives the benefit must be age 65 or older" in senior
    assert "Citizenship: required for the person who receives the benefit." in senior
    assert "Requires that the person who receives the benefit is pregnant." in body_of(
        chunk_for("example_pregnancy_care_tx", "eligibility"))


def test_null_fields_are_rendered_honestly():
    disability = body_of(chunk_for("example_disability_income_federal", "eligibility"))
    assert disability.startswith("No single percent-of-poverty income limit is recorded for this program")
    apply_text = body_of(chunk_for("example_disability_income_federal", "apply"))
    assert "Documents needed: not recorded." in apply_text
    assert "Estimated monthly value: not recorded." in apply_text
    assert "Processing time: 120 days." in apply_text
    food_apply = body_of(chunk_for("example_food_help_federal", "apply"))
    assert "Documents needed: ID, Proof of income." in food_apply
    assert "Estimated monthly value: $250.50." in food_apply


def test_load_programs_validates_and_rejects_bad_files(tmp_path):
    assert len(load_programs(write_programs_dir(tmp_path / "good"))) == len(FIXTURE_PROGRAMS)
    dup = write_programs_dir(tmp_path / "dup")
    (dup / "more.json").write_text(json.dumps([FIXTURE_PROGRAMS[0].model_dump()]), encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate"):
        load_programs(dup)
    bad = tmp_path / "bad"
    bad.mkdir()
    (bad / "broken.json").write_text(json.dumps([{"program_id": "x"}]), encoding="utf-8")
    with pytest.raises(ValueError, match="broken.json"):
        load_programs(bad)


def test_rebuild_is_idempotent_and_matches_computed_chunks(tmp_path):
    store = ChunkStore(tmp_path / "chroma", HashEmbedding())
    assert store.count() == 0 and not (tmp_path / "chroma").exists()
    expected = len(chunk_programs(FIXTURE_PROGRAMS))
    assert store.rebuild(FIXTURE_PROGRAMS) == expected
    assert store.count() == expected
    assert store.rebuild(FIXTURE_PROGRAMS) == expected
    assert store.count() == expected
    assert store.rebuild(FIXTURE_PROGRAMS[:2]) < expected and store.count() < expected
    hits = ChunkStore(tmp_path / "chroma", HashEmbedding()).query(
        ["grocery money for food"], 3, where={"state": "US"})
    assert len(hits) == 1 and 0 < len(hits[0]) <= 3
    assert all(h["metadata"]["state"] == "US" for h in hits[0])


def test_check_detects_stale_index(tmp_path, capsys):
    script = load_script()
    programs_dir = write_programs_dir(tmp_path / "programs")
    args = ["--programs-dir", str(programs_dir), "--chroma-dir", str(tmp_path / "chroma")]
    ef = HashEmbedding()

    assert script.main(args + ["--check"], ef) == 1
    assert capsys.readouterr().out.strip() == "INDEX STALE"

    assert script.main(args, ef) == 0
    first = capsys.readouterr().out.strip()
    assert re.fullmatch(rf"Indexed {len(FIXTURE_PROGRAMS)} programs, \d+ chunks into .+", first)
    assert script.main(args, ef) == 0
    assert capsys.readouterr().out.strip() == first
    assert script.main(args + ["--check"], ef) == 0
    assert capsys.readouterr().out.strip() == "INDEX OK"

    write_programs_dir(programs_dir, FIXTURE_PROGRAMS[:-1])
    assert script.main(args + ["--check"], ef) == 1
    assert capsys.readouterr().out.strip() == "INDEX STALE"
    # Same IDs but different text is stale too.
    edited = [FIXTURE_PROGRAMS[0].model_copy(update={"description": "A different description."})]
    write_programs_dir(programs_dir, edited + FIXTURE_PROGRAMS[1:])
    assert script.main(args + ["--check"], ef) == 1
    assert capsys.readouterr().out.strip() == "INDEX STALE"


def test_script_reports_unreadable_programs(tmp_path, capsys):
    script = load_script()
    empty = tmp_path / "empty"
    empty.mkdir()
    assert script.main(["--programs-dir", str(empty), "--chroma-dir", str(tmp_path / "c")], HashEmbedding()) == 2
    assert "no programs found" in capsys.readouterr().err


def test_command_line_with_real_default_embedding(tmp_path):
    default_embedding_or_skip()
    programs_dir = write_programs_dir(tmp_path / "programs")
    chroma_dir = tmp_path / "chroma"
    base = [sys.executable, str(INDEX_SCRIPT), "--programs-dir", str(programs_dir), "--chroma-dir", str(chroma_dir)]
    run = lambda *extra: subprocess.run(base + list(extra), capture_output=True, text=True, timeout=300)  # noqa: E731

    built = run()
    assert built.returncode == 0, built.stderr
    expected = len(chunk_programs(FIXTURE_PROGRAMS))
    assert built.stdout.strip() == f"Indexed {len(FIXTURE_PROGRAMS)} programs, {expected} chunks into {chroma_dir}"
    checked = run("--check")
    assert (checked.returncode, checked.stdout.strip()) == (0, "INDEX OK")

    store = ChunkStore(chroma_dir)
    assert store.count() == expected
    top = store.query(["help paying for medicine for an older adult"], 1)[0][0]
    assert top["metadata"]["program_id"] == "example_senior_drug_help_federal"
