"""AMR relevance filtering. Keyword-first; concept IDs as supplement."""

import json
import re
from pathlib import Path

_CONFIG_PATH = Path(__file__).parent.parent / "config" / "amr_concepts.json"


def _load_config() -> dict:
    with open(_CONFIG_PATH) as f:
        return json.load(f)


def _reconstruct_abstract(inverted_index: dict | None) -> str:
    """OpenAlex stores abstracts as inverted index {word: [positions]}."""
    if not inverted_index:
        return ""
    max_pos = max(pos for positions in inverted_index.values() for pos in positions)
    words = [""] * (max_pos + 1)
    for word, positions in inverted_index.items():
        for pos in positions:
            words[pos] = word
    return " ".join(words)


def load_amr_keywords() -> list[str]:
    return _load_config()["keywords"]


def load_amr_concept_ids() -> list[str]:
    return [c["id"] for c in _load_config()["openalex_concept_ids"]]


def is_amr_related(work: dict, keywords: list[str] | None = None) -> bool:
    """Return True if title or abstract contains any AMR keyword (case-insensitive)."""
    if keywords is None:
        keywords = load_amr_keywords()

    title = (work.get("title") or "").lower()
    abstract = _reconstruct_abstract(work.get("abstract_inverted_index")).lower()
    text = f"{title} {abstract}"

    pattern = "|".join(re.escape(kw.lower()) for kw in keywords)
    return bool(re.search(pattern, text))


def extract_priority_authors(work: dict) -> list[dict]:
    """Return first 5 + last 5 authorships, deduplicated, preserving order."""
    authorships = work.get("authorships", [])
    if not authorships:
        return []
    priority = authorships[:5] + authorships[-5:]
    seen, result = set(), []
    for a in priority:
        aid = a.get("author", {}).get("id")
        if aid and aid not in seen:
            seen.add(aid)
            result.append(a)
    return result
