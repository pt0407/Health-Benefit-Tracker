"""Thin wrapper around a persistent ChromaDB collection of program chunks.

Uses cosine distance and, unless one is injected, ChromaDB's built-in default
embedding function (local model, no API key).
"""

import json
from pathlib import Path
from typing import Optional, Sequence

import chromadb
from chromadb.config import Settings
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction

from config import CHROMA_DIR, PROGRAMS_DIR
from models.program import Program
from rag.chunker import chunk_programs

COLLECTION_NAME = "benefit_programs"
_BATCH = 100


def load_programs(programs_dir: Optional[Path] = None) -> list[Program]:
    """Load and validate every *.json file in programs_dir (default: config.PROGRAMS_DIR)."""
    directory = Path(programs_dir) if programs_dir else PROGRAMS_DIR
    programs: list[Program] = []
    for path in sorted(directory.glob("*.json")):
        try:
            records = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(records, list):
                raise ValueError("expected a JSON list of programs")
            programs.extend(Program.model_validate(r) for r in records)
        except (OSError, ValueError) as exc:
            raise ValueError(f"{path.name}: {exc}") from exc
    ids = [p.program_id for p in programs]
    duplicates = sorted({i for i in ids if ids.count(i) > 1})
    if duplicates:
        raise ValueError(f"duplicate program_id values: {', '.join(duplicates)}")
    return programs


class ChunkStore:
    def __init__(self, persist_dir: Optional[Path] = None, embedding_function=None,
                 collection_name: str = COLLECTION_NAME) -> None:
        self.persist_dir = Path(persist_dir) if persist_dir else CHROMA_DIR
        self.collection_name = collection_name
        self._embedding_function = embedding_function or DefaultEmbeddingFunction()
        self._client = None

    def _get_client(self, create: bool):
        # A missing directory means "no index"; do not create one just to look.
        if self._client is None:
            if not create and not self.persist_dir.exists():
                return None
            self._client = chromadb.PersistentClient(
                path=str(self.persist_dir), settings=Settings(anonymized_telemetry=False))
        return self._client

    def _collection(self):
        client = self._get_client(create=False)
        if client is None:
            return None
        if self.collection_name not in {c.name for c in client.list_collections()}:
            return None
        return client.get_collection(self.collection_name, embedding_function=self._embedding_function)

    def rebuild(self, programs: list[Program]) -> int:
        """Drop and recreate the collection from programs. Returns the chunk count."""
        chunks = chunk_programs(programs)
        client = self._get_client(create=True)
        if self.collection_name in {c.name for c in client.list_collections()}:
            client.delete_collection(self.collection_name)
        collection = client.create_collection(
            self.collection_name, embedding_function=self._embedding_function,
            metadata={"hnsw:space": "cosine"})
        for start in range(0, len(chunks), _BATCH):
            batch = chunks[start:start + _BATCH]
            collection.add(ids=[c.id for c in batch], documents=[c.text for c in batch],
                           metadatas=[c.metadata for c in batch])
        return len(chunks)

    def count(self) -> int:
        collection = self._collection()
        return collection.count() if collection is not None else 0

    def stored_documents(self) -> dict[str, str]:
        """Map of chunk id to chunk text currently in the index."""
        collection = self._collection()
        if collection is None:
            return {}
        stored = collection.get(include=["documents"])
        return dict(zip(stored["ids"], stored["documents"]))

    def is_current(self, programs: list[Program]) -> bool:
        """True when the stored chunk IDs and texts equal those computed from programs."""
        return self.stored_documents() == {c.id: c.text for c in chunk_programs(programs)}

    def query(self, texts: Sequence[str], n_results: int, where: Optional[dict] = None) -> list[list[dict]]:
        """One ranked hit list per query text: dicts with id, text, metadata, distance."""
        collection = self._collection()
        total = collection.count() if collection is not None else 0
        if not total:
            return [[] for _ in texts]
        result = collection.query(query_texts=list(texts), n_results=min(n_results, total),
                                  where=where, include=["documents", "metadatas", "distances"])
        return [
            [{"id": i, "text": t, "metadata": m, "distance": d}
             for i, t, m, d in zip(result["ids"][q], result["documents"][q],
                                   result["metadatas"][q], result["distances"][q])]
            for q in range(len(texts))
        ]
