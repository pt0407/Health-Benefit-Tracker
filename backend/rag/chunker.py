"""Turn a Program record into self-describing text chunks for the vector index.

Chunk text only restates fields of the record. A false boolean flag is omitted
instead of being rendered as a negative claim, and null fields are stated as
not recorded. See AUTON/PLAN.md Appendix C1 and C2 for the format.
"""

import re
from dataclasses import dataclass

from models.program import Program

SECTIONS = ("overview", "eligibility", "apply")
MAX_BODY_WORDS = 300
OVERLAP_WORDS = 50
RECIPIENT = "the person who receives the benefit"
_SENTENCE_BREAK = re.compile(r"(?<=[.!?])\s+")


@dataclass(frozen=True)
class Chunk:
    id: str
    text: str
    metadata: dict


def state_for(program_id: str) -> str:
    return "TX" if program_id.endswith("_tx") else "US"


def _words(parts: list[str]) -> int:
    return sum(len(p.split()) for p in parts)


def split_body(units: list[str], joiner: str = " ", max_words: int = MAX_BODY_WORDS,
               overlap: int = OVERLAP_WORDS) -> list[str]:
    """Pack sentences into bodies of at most max_words words.

    Splits only between sentences and repeats up to `overlap` trailing words of
    one body at the start of the next. A single sentence longer than max_words
    is cut on word boundaries as a last resort.
    """
    pieces: list[str] = []
    for unit in units:
        words = unit.split()
        start = 0
        while len(words) - start > max_words:
            pieces.append(" ".join(words[start:start + max_words]))
            start += max_words - overlap
        pieces.append(" ".join(words[start:]) if start else unit)
    bodies: list[str] = []
    current: list[str] = []
    for piece in pieces:
        size = len(piece.split())
        if current and _words(current) + size > max_words:
            bodies.append(joiner.join(current))
            tail: list[str] = []
            for earlier in reversed(current):
                if _words(tail) + len(earlier.split()) > overlap:
                    break
                tail.insert(0, earlier)
            while tail and _words(tail) + size > max_words:
                tail.pop(0)
            current = tail
        current.append(piece)
    if current:
        bodies.append(joiner.join(current))
    return bodies


def _money(value: float) -> str:
    return f"${value:,.0f}" if float(value).is_integer() else f"${value:,.2f}"


def eligibility_lines(program: Program) -> list[str]:
    e = program.eligibility
    if e.income_limit_pct_fpl is None:
        lines = ["No single percent-of-poverty income limit is recorded for this program; "
                 "see the description."]
    else:
        lines = [f"Income limit: up to {e.income_limit_pct_fpl:g} percent of the federal poverty level."]
    if e.age_min is not None and e.age_max is not None:
        lines.append(f"Age: {RECIPIENT} must be age {e.age_min} to {e.age_max}.")
    elif e.age_min is not None:
        lines.append(f"Age: {RECIPIENT} must be age {e.age_min} or older.")
    elif e.age_max is not None:
        lines.append(f"Age: {RECIPIENT} must be age {e.age_max} or younger.")
    if e.citizenship_required:
        lines.append(f"Citizenship: required for {RECIPIENT}.")
    if e.requires_children:
        lines.append("Requires children in the household.")
    if e.requires_disability:
        lines.append(f"Requires that {RECIPIENT} has a disability.")
    if e.requires_pregnancy:
        lines.append(f"Requires that {RECIPIENT} is pregnant.")
    return lines


def apply_lines(program: Program) -> list[str]:
    docs = ", ".join(d.strip().rstrip(".") for d in program.documents_needed if d.strip())
    days = program.processing_time_days
    value = program.estimated_monthly_value_usd
    return [
        f"Documents needed: {docs}." if docs else "Documents needed: not recorded.",
        f"Processing time: {days} {'day' if days == 1 else 'days'}." if days is not None
        else "Processing time: not recorded.",
        f"Estimated monthly value: {_money(value)}." if value is not None
        else "Estimated monthly value: not recorded.",
    ]


def render_chunk_text(program: Program, body: str) -> str:
    return (
        f"Program: {program.name} [{program.program_id}]\n"
        f"Type: {program.type} | Category: {program.category} | Source: {program.source} "
        f"| Last updated: {program.last_updated}\n"
        f"{body}\n"
        f"Apply: {program.application_url}"
    )


def chunk_metadata(program: Program, section: str, index: int) -> dict:
    e = program.eligibility
    return {
        "program_id": program.program_id,
        "program_name": program.name,
        "type": program.type,
        "category": program.category,
        "state": state_for(program.program_id),
        "source": program.source,
        "section": section,
        "chunk_index": index,
        "requires_children": e.requires_children,
        "requires_disability": e.requires_disability,
        "requires_pregnancy": e.requires_pregnancy,
    }


def chunk_program(program: Program) -> list[Chunk]:
    description = " ".join(program.description.split())
    units = {
        "overview": ([s for s in _SENTENCE_BREAK.split(description) if s], " "),
        "eligibility": (eligibility_lines(program), "\n"),
        "apply": (apply_lines(program), "\n"),
    }
    chunks = []
    for section in SECTIONS:
        sentences, joiner = units[section]
        for n, body in enumerate(split_body(sentences, joiner)):
            chunks.append(Chunk(
                id=f"{program.program_id}:{section}:{n}",
                text=render_chunk_text(program, body),
                metadata=chunk_metadata(program, section, n),
            ))
    return chunks


def chunk_programs(programs: list[Program]) -> list[Chunk]:
    ids = [p.program_id for p in programs]
    duplicates = sorted({i for i in ids if ids.count(i) > 1})
    if duplicates:
        raise ValueError(f"duplicate program_id values: {', '.join(duplicates)}")
    return [chunk for program in programs for chunk in chunk_program(program)]
