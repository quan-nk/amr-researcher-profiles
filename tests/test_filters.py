from src.filters import is_amr_related, extract_priority_authors, _reconstruct_abstract


def _work(title="", abstract_words=None, n_authors=5):
    abstract_index = None
    if abstract_words:
        abstract_index = {word: [i] for i, word in enumerate(abstract_words)}
    authorships = [{"author": {"id": f"A{i}", "display_name": f"Author {i}"}} for i in range(n_authors)]
    return {"title": title, "abstract_inverted_index": abstract_index, "authorships": authorships}


def test_amr_keyword_in_title():
    assert is_amr_related(_work(title="Carbapenem resistance in Klebsiella"))


def test_amr_keyword_in_abstract():
    work = _work(abstract_words=["rates", "of", "ESBL", "production"])
    assert is_amr_related(work)


def test_non_amr_paper_rejected():
    assert not is_amr_related(_work(title="Diabetes management in elderly patients"))


def test_extract_priority_deduplicates():
    work = _work(n_authors=3)
    authors = extract_priority_authors(work)
    ids = [a["author"]["id"] for a in authors]
    assert len(ids) == len(set(ids))


def test_extract_priority_ten_authors():
    work = _work(n_authors=10)
    priority = extract_priority_authors(work)
    assert len(priority) == 10


def test_extract_priority_five_authors():
    work = _work(n_authors=5)
    priority = extract_priority_authors(work)
    assert len(priority) == 5


def test_extract_priority_two_authors():
    work = _work(n_authors=2)
    priority = extract_priority_authors(work)
    assert len(priority) == 2


def test_reconstruct_abstract():
    inverted = {"hello": [0], "world": [1]}
    assert _reconstruct_abstract(inverted) == "hello world"


def test_reconstruct_abstract_none():
    assert _reconstruct_abstract(None) == ""
