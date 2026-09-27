"""Component 4 — RAG Engine. Owner: Person 2.

See docs/BUILD_PLAN.md §3 Component 4. Note: Anthropic has no embeddings API,
so use ChromaDB's default embedding function instead of `AnthropicEmbeddings`.
The vector DB persists to config.CHROMA_DIR (gitignored).
"""

from models.program import Program
from models.user_profile import UserProfile


class BenefitsRAG:
    def retrieve_relevant_programs(self, profile: UserProfile, k: int = 10) -> list[str]:
        raise NotImplementedError

    def index_programs(self, programs: list[Program]) -> None:
        raise NotImplementedError
