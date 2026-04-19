import sys
from datetime import datetime, date

import click

from .resolve import from_scholar_url, from_name
from .snowball import run
from .export import save
from .openalex import verify_concepts, get_works_for_author, get_author
from .filters import load_amr_concept_ids, load_amr_keywords, is_amr_related

_SCREEN_YEARS = 5


@click.command()
@click.option("--scholar", default=None, help="Google Scholar profile URL")
@click.option("--author", default=None, help="Author name (alternative to --scholar)")
@click.option("--author-id", default=None, help="OpenAlex author ID (skips resolution)")
@click.option("--institution", default=None, help="Institution to narrow author search")
@click.option("--depth", default=3, show_default=True, help="BFS depth limit")
@click.option("--output", default=None, help="Output directory (default: data/processed/{timestamp})")
@click.option("--rate-limit", default=1.0, show_default=True, help="Seconds between API calls")
@click.option("--verify-concepts", "do_verify", is_flag=True, help="Check AMR concept IDs against OpenAlex and exit")
@click.option("--screen", is_flag=True, help=f"Skip seed if no AMR publication in last {_SCREEN_YEARS} years")
@click.option("--min-hindex", default=0, show_default=True, help="Skip seed if h-index is below this threshold")
@click.option("--auto-select", is_flag=True, help="Auto-select first OpenAlex candidate (non-interactive)")
@click.option("--resume", is_flag=True, help="Resume BFS from checkpoint in --output dir")
@click.option("--checkpoint-every", default=50, show_default=True, help="Save checkpoint every N authors")
@click.option("--max-authors", default=0, show_default=True, help="Stop BFS after N authors (0 = unlimited)")
def main(scholar, author, author_id, institution, depth, output, rate_limit, do_verify, screen, min_hindex, auto_select, resume, checkpoint_every, max_authors):
    """Snowball-mine AMR research networks from a seed researcher."""

    if do_verify:
        _verify_concepts(rate_limit)
        return

    author_id = author_id or _resolve_author(scholar, author, institution, rate_limit, auto_select)
    if not author_id:
        click.echo("Could not resolve author. Try --author 'Full Name' --institution 'Org'", err=True)
        sys.exit(1)

    if min_hindex > 0 and not _passes_hindex_screen(author_id, min_hindex, rate_limit):
        return

    if screen and not _passes_amr_screen(author_id, rate_limit):
        click.echo(f"SKIP {author_id}: no AMR publication in last {_SCREEN_YEARS} years.")
        return

    out_dir = output or f"data/processed/{datetime.utcnow().strftime('%Y%m%dT%H%M%S')}"
    click.echo(f"Seed author ID: {author_id}  depth={depth}  output={out_dir}")

    result = run(
        author_id,
        depth=depth,
        rate_limit=rate_limit,
        checkpoint_dir=out_dir,
        checkpoint_every=checkpoint_every,
        resume=resume,
        max_authors=max_authors,
        min_hindex=min_hindex,
        screen_years=_SCREEN_YEARS if screen else 0,
    )

    saved_to = save(result, out_dir, seed_id=author_id, depth=depth)

    click.echo(f"\nDone. {len(result.authors)} authors, {len(result.papers)} AMR papers.")
    click.echo(f"Output: {saved_to}")


def _resolve_author(scholar, author, institution, rate_limit, auto_select):
    if scholar:
        author_id = from_scholar_url(scholar, rate_limit)
        if author_id:
            return author_id
        click.echo("Could not auto-resolve Scholar URL. Falling back to --author if provided.")

    if author:
        return from_name(author, institution, rate_limit, auto_select=auto_select)

    click.echo("Provide --scholar or --author.", err=True)
    return None


def _passes_hindex_screen(author_id: str, min_hindex: int, rate_limit: float) -> bool:
    profile = get_author(author_id, rate_limit)
    h = profile.get("summary_stats", {}).get("h_index", 0) or 0
    name = profile.get("display_name", author_id)
    if h < min_hindex:
        click.echo(f"SKIP {name}: h-index {h} < {min_hindex}.")
        return False
    return True


def _passes_amr_screen(author_id: str, rate_limit: float) -> bool:
    from_year = date.today().year - _SCREEN_YEARS
    keywords = load_amr_keywords()
    works = get_works_for_author(author_id, from_year=from_year, rate_limit=rate_limit)
    return any(is_amr_related(w, keywords) for w in works)


def _verify_concepts(rate_limit):
    ids = load_amr_concept_ids()
    results = verify_concepts(ids, rate_limit)
    for r in results:
        status = "OK" if r["valid"] else "NOT FOUND"
        click.echo(f"  [{status}] {r['id']} — {r['name']}")


if __name__ == "__main__":
    main()
