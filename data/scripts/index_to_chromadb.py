"""Rebuild or check the ChromaDB index of benefit program chunks.

Run from the repo root with the backend venv active:

    python data/scripts/index_to_chromadb.py            # rebuild data/chroma_db/
    python data/scripts/index_to_chromadb.py --check    # INDEX OK or INDEX STALE

The index is generated and gitignored; it is rebuilt from data/programs/*.json.
"""

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from config import CHROMA_DIR, PROGRAMS_DIR  # noqa: E402
from rag.store import ChunkStore, load_programs  # noqa: E402


def main(argv=None, embedding_function=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--programs-dir", type=Path, default=PROGRAMS_DIR)
    parser.add_argument("--chroma-dir", type=Path, default=CHROMA_DIR)
    parser.add_argument("--check", action="store_true",
                        help="report whether the stored index matches the current data")
    args = parser.parse_args(argv)

    try:
        programs = load_programs(args.programs_dir)
    except ValueError as exc:
        print(f"ERROR {exc}", file=sys.stderr)
        return 2
    if not programs:
        print(f"ERROR no programs found in {args.programs_dir}", file=sys.stderr)
        return 2

    store = ChunkStore(args.chroma_dir, embedding_function)
    if args.check:
        if store.is_current(programs):
            print("INDEX OK")
            return 0
        print("INDEX STALE")
        return 1
    chunk_count = store.rebuild(programs)
    print(f"Indexed {len(programs)} programs, {chunk_count} chunks into {args.chroma_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
