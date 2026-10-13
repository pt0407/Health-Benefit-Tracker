"""Run the named retrieval expectations against the committed program records.

    python data/scripts/check_retrieval.py [--chroma-dir PATH]

Without --chroma-dir a temporary index is built from data/programs/*.json.
"""

import argparse
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from config import PROGRAMS_DIR  # noqa: E402
from rag.eval_profiles import EVAL_PROFILES, evaluate  # noqa: E402
from rag.rag_engine import BenefitsRAG  # noqa: E402
from rag.store import load_programs  # noqa: E402


def run(chroma_dir: Path) -> int:
    rag = BenefitsRAG(persist_dir=chroma_dir)
    passed = failed = 0
    for ev in EVAL_PROFILES:
        ok, missing, unexpected, ids = evaluate(rag, ev)
        if ok:
            passed += 1
            print(f"PASS {ev.name}: {', '.join(ids)}")
        else:
            failed += 1
            print(f"FAIL {ev.name}: missing={','.join(missing)} "
                  f"unexpected={','.join(unexpected)} got={','.join(ids)}")
    print(f"SUMMARY pass={passed} fail={failed}")
    return 1 if failed else 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--chroma-dir", type=Path, default=None)
    args = parser.parse_args(argv)
    if args.chroma_dir is not None:
        return run(args.chroma_dir)
    with tempfile.TemporaryDirectory() as tmp:
        persist = Path(tmp) / "chroma"
        BenefitsRAG(persist_dir=persist).index_programs(load_programs(PROGRAMS_DIR))
        return run(persist)


if __name__ == "__main__":
    sys.exit(main())
