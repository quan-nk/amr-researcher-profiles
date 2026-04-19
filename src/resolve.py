"""Resolve a Google Scholar URL or author name to an OpenAlex author ID."""

import re
import click
from .openalex import search_authors


def from_scholar_url(url: str, rate_limit: float = 1.0) -> str | None:
    """
    Best-effort: fetch the Scholar page title to extract the author name,
    then delegate to from_name(). Scholar often blocks headless requests,
    so this may require the user to provide --author as fallback.
    """
    try:
        import requests
        headers = {"User-Agent": "Mozilla/5.0 (compatible; AMRSnowball/1.0)"}
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        match = re.search(r"<title>([^<]+)</title>", resp.text, re.IGNORECASE)
        if match:
            raw = re.sub(r"[\u200e\u200f\u202a-\u202e\u2066-\u2069]", "", match.group(1))
            name = raw.replace(" - Google Scholar", "").strip()
            return from_name(name, rate_limit=rate_limit)
    except Exception:
        pass
    return None


def from_name(
    name: str,
    institution: str | None = None,
    rate_limit: float = 1.0,
    auto_select: bool = False,
) -> str | None:
    """Search OpenAlex for the author and prompt user to confirm if multiple matches."""
    candidates = search_authors(name, institution, rate_limit)
    if not candidates:
        return None
    if len(candidates) == 1 or auto_select:
        return candidates[0]["id"]

    click.echo(f"\nFound {len(candidates)} candidates for '{name}':")
    for i, c in enumerate(candidates[:5]):
        inst = (c.get("last_known_institution") or {}).get("display_name", "unknown institution")
        h = c.get("summary_stats", {}).get("h_index", "?")
        click.echo(f"  [{i}] {c['display_name']} — {inst} — h-index: {h}")

    idx = click.prompt("Select author index", type=int, default=0)
    return candidates[idx]["id"]
