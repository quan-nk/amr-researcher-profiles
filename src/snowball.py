"""BFS snowball traversal over the AMR co-author network."""

from __future__ import annotations
from collections import deque
from dataclasses import dataclass, field
from datetime import date
from tqdm import tqdm

from .openalex import get_author, get_works_for_author
from .filters import is_amr_related, extract_priority_authors, load_amr_keywords, load_amr_concept_ids
from .export import save_checkpoint, load_checkpoint


@dataclass
class SnowballResult:
    authors: dict[str, dict] = field(default_factory=dict)   # author_id → profile
    papers: dict[str, dict] = field(default_factory=dict)    # paper_id → paper
    edges: list[tuple[str, str, str]] = field(default_factory=list)  # (a_id, b_id, paper_id)


def run(
    seed_author_id: str,
    depth: int = 3,
    rate_limit: float = 1.0,
    checkpoint_dir: str | None = None,
    checkpoint_every: int = 50,
    resume: bool = False,
    max_authors: int = 0,
    min_hindex: int = 0,
    screen_years: int = 0,
) -> SnowballResult:
    """
    BFS from seed_author_id. Stops when max_authors qualifying authors are collected,
    or when total visited nodes exceeds max_authors*8 (safety valve), or queue empties.
    """
    keywords = load_amr_keywords()
    concept_ids = load_amr_concept_ids()

    if resume and checkpoint_dir:
        checkpoint = load_checkpoint(checkpoint_dir)
        if checkpoint:
            result, visited, queue = checkpoint
            print(f"Resuming: {len(visited)} authors done, {len(queue)} queued.")
        else:
            print("No checkpoint found — starting fresh.")
            result, visited, queue = SnowballResult(), set(), deque([(seed_author_id, 0)])
    else:
        result, visited, queue = SnowballResult(), set(), deque([(seed_author_id, 0)])

    n_processed = 0

    visited_cap = max_authors * 8 if max_authors else 0

    with tqdm(desc="Mining network", unit="author", initial=len(visited)) as pbar:
        while queue:
            author_id, current_depth = queue.popleft()

            if author_id in visited:
                continue
            if max_authors and len(result.authors) >= max_authors:
                break
            if visited_cap and len(visited) >= visited_cap:
                break
            visited.add(author_id)
            pbar.update(1)
            n_processed += 1

            if checkpoint_dir and n_processed % checkpoint_every == 0:
                save_checkpoint(result, visited, queue, checkpoint_dir)

            author_profile = get_author(author_id, rate_limit)

            if min_hindex > 0:
                h = author_profile.get("summary_stats", {}).get("h_index", 0) or 0
                if h < min_hindex:
                    continue

            from_year = date.today().year - screen_years if screen_years > 0 else None
            works = get_works_for_author(
                author_id,
                concept_ids=concept_ids,
                from_year=from_year,
                rate_limit=rate_limit,
            )
            amr_works = [w for w in works if is_amr_related(w, keywords)]

            if screen_years > 0:
                cutoff = date.today().year - screen_years
                if not any((w.get("publication_year") or 0) >= cutoff for w in amr_works):
                    continue

            result.authors[author_id] = {
                "id": author_id,
                "name": author_profile.get("display_name"),
                "institution": _extract_institution(author_profile),
                "h_index": author_profile.get("summary_stats", {}).get("h_index"),
                "works_count": author_profile.get("works_count"),
                "depth_found": current_depth,
                "amr_paper_count": len(amr_works),
            }

            for work in amr_works:
                paper_id = work.get("id")
                if paper_id and paper_id not in result.papers:
                    result.papers[paper_id] = _flatten_paper(work)

                if current_depth < depth:
                    for authorship in extract_priority_authors(work):
                        co_id = authorship.get("author", {}).get("id")
                        if co_id and co_id not in visited:
                            queue.append((co_id, current_depth + 1))
                            if paper_id:
                                result.edges.append((author_id, co_id, paper_id))

    if checkpoint_dir:
        save_checkpoint(result, visited, queue, checkpoint_dir)

    return result


def _extract_institution(profile: dict) -> str | None:
    inst = profile.get("last_known_institution") or {}
    return inst.get("display_name")


def _flatten_paper(work: dict) -> dict:
    location = work.get("primary_location") or {}
    source = location.get("source") or {}
    authors = [
        a.get("author", {}).get("display_name")
        for a in work.get("authorships", [])
    ]
    concepts = [c.get("display_name") for c in work.get("concepts", [])[:5]]
    return {
        "id": work.get("id"),
        "doi": work.get("doi"),
        "title": work.get("title"),
        "year": work.get("publication_year"),
        "journal": source.get("display_name"),
        "authors": "; ".join(filter(None, authors)),
        "concepts": "; ".join(filter(None, concepts)),
    }
