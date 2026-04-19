"""All HTTP interaction with api.openalex.org. No other module calls requests directly."""

import os
import time
import requests

BASE_URL = "https://api.openalex.org"
_email = os.getenv("OPENALEX_EMAIL", "")


def _params(**kwargs) -> dict:
    p = {k: v for k, v in kwargs.items() if v is not None}
    if _email:
        p["mailto"] = _email
    return p


def _get(endpoint: str, params: dict, rate_limit: float = 1.0) -> dict:
    time.sleep(rate_limit)
    url = f"{BASE_URL}/{endpoint}"
    for attempt in range(4):
        try:
            resp = requests.get(url, params=params, timeout=60)
            resp.raise_for_status()
            return resp.json()
        except (requests.Timeout, requests.ConnectionError) as e:
            if attempt == 3:
                raise
            time.sleep(2 ** attempt)
        except requests.HTTPError as e:
            status = e.response.status_code
            if attempt == 3 or (status not in (429,) and status < 500):
                raise
            wait = int(e.response.headers.get("Retry-After", 2 ** (attempt + 2)))
            time.sleep(wait)


def search_authors(name: str, institution: str | None = None, rate_limit: float = 1.0) -> list[dict]:
    """Return ranked list of candidate authors matching name (+ optional institution)."""
    filter_str = f"display_name.search:{name}"
    if institution:
        filter_str += f",last_known_institution.display_name.search:{institution}"
    data = _get("authors", _params(filter=filter_str, per_page=10), rate_limit)
    return data.get("results", [])


def get_author(author_id: str, rate_limit: float = 1.0) -> dict:
    """Fetch full author record by OpenAlex ID (e.g. 'A2208157607')."""
    return _get(f"authors/{author_id}", _params(), rate_limit)


def get_works_for_author(
    author_id: str,
    concept_ids: list[str] | None = None,
    from_year: int | None = None,
    title_search: str | None = None,
    per_page: int = 200,
    rate_limit: float = 1.0,
) -> list[dict]:
    """Paginate through works for an author, optionally filtered by concept IDs, year, and title/abstract search."""
    filter_str = f"author.id:{author_id}"
    if concept_ids:
        filter_str += f",concepts.id:{'|'.join(concept_ids)}"
    if from_year:
        filter_str += f",publication_year:>{from_year - 1}"
    if title_search:
        filter_str += f",title_and_abstract.search:{title_search}"

    works, cursor = [], "*"
    while cursor:
        data = _get(
            "works",
            _params(filter=filter_str, per_page=per_page, cursor=cursor, select="id,doi,title,publication_year,primary_location,authorships,abstract_inverted_index,concepts"),
            rate_limit,
        )
        works.extend(data.get("results", []))
        cursor = data.get("meta", {}).get("next_cursor")

    return works


def verify_concepts(concept_ids: list[str], rate_limit: float = 1.0) -> list[dict]:
    """Check that concept IDs exist and return their display names."""
    results = []
    for cid in concept_ids:
        try:
            data = _get(f"concepts/{cid}", _params(), rate_limit)
            results.append({"id": cid, "name": data.get("display_name"), "valid": True})
        except requests.HTTPError:
            results.append({"id": cid, "name": None, "valid": False})
    return results
