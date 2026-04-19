# AMR Researcher Profiles

A snowball-sampling framework for mapping antimicrobial resistance (AMR) research networks. Starting from a single researcher's Google Scholar profile, it recursively mines co-author networks, retaining only AMR-relevant papers, until the network converges.

Built to support evidence synthesis for AMR burden estimation in Vietnam and Southeast Asia.

---

## How It Works

```
Seed researcher (Google Scholar URL or name)
        │
        ▼
  Resolve → OpenAlex author ID
        │
        ▼
  Fetch all AMR-related papers
  (filter by keywords + OpenAlex concepts)
        │
        ▼
  Extract priority co-authors
  (first 3 authors + last 2 per paper)
        │
        ▼
  Add new authors to queue
        │
        └──► Repeat until queue empty or depth limit reached
                        │
                        ▼
              Output: authors, papers, network edge list
```

**Convergence** occurs when a full BFS round adds no new unvisited authors. Default depth limit: 3 hops.

---

## Installation

Requires Python 3.11+.

```bash
git clone https://github.com/quan-nk/amr-researcher-profiles
cd amr-researcher-profiles
pip install -r requirements.txt
```

No API keys required for basic use. OpenAlex is free and open.

Optional: add your email to requests for higher rate limits (10 req/sec vs 1 req/sec):

```bash
export OPENALEX_EMAIL="your@email.com"
```

---

## Usage

### By Google Scholar URL
```bash
python -m src.cli --scholar "https://scholar.google.com/citations?user=XXXXXXX"
```

### By author name
```bash
python -m src.cli --author "Guy Thwaites" --institution "OUCRU"
```

### Full options
```bash
python -m src.cli \
  --author "Marc Choisy" \
  --institution "OUCRU" \
  --depth 2 \
  --output data/processed/my_run/
```

| Flag | Default | Description |
|---|---|---|
| `--scholar` | — | Google Scholar profile URL |
| `--author` | — | Author name (alternative to --scholar) |
| `--institution` | — | Narrows author search |
| `--depth` | 3 | Maximum BFS hops |
| `--output` | `data/processed/{timestamp}/` | Output directory |
| `--rate-limit` | 1.0 | Seconds between API calls |

---

## Output

```
data/processed/{run_id}/
├── authors.csv       — OpenAlex ID, name, institution, h-index, AMR paper count, depth found
├── papers.csv        — DOI, title, year, journal, full author list, OpenAlex concepts
├── network.csv       — author_a_id, author_b_id, shared_paper_count (edge list)
└── run_meta.json     — seed, depth, timestamps, total authors/papers
```

`network.csv` is importable directly into Gephi, NetworkX, or R's igraph.

---

## AMR Filter

Papers are retained if they match any of the following in title or abstract:

- `antimicrobial resistance`, `antibiotic resistance`, `AMR`, `drug resistance`
- `MRSA`, `ESBL`, `carbapenem`, `MDR`, `XDR`, `PDR`
- `beta-lactamase`, `susceptibility testing`, `WHONET`, `GLASS`
- `colistin`, `vancomycin resistance`, `fluoroquinolone resistance`

Edit `config/amr_concepts.json` to add or remove terms without touching source code.

---

## Data Sources

| Source | Used for |
|---|---|
| [OpenAlex](https://openalex.org) | Author profiles, paper metadata, co-author lists |
| [PubMed](https://pubmed.ncbi.nlm.nih.gov) | Abstract retrieval, cross-reference |

No Google Scholar scraping. OpenAlex mirrors Scholar data for academic works and provides a stable, documented API.

---

## Limitations

- OpenAlex coverage is strong for journal articles but may miss Vietnamese-language publications and grey literature
- Author disambiguation: common Vietnamese names (e.g., Nguyen Van X) may match multiple authors — the tool returns ranked candidates and asks for confirmation
- Co-authorship network reflects publication patterns, not actual collaboration intensity

---

## Contributing

Pull requests welcome. Please:
- Keep new features behind CLI flags (don't change default behavior)
- Add fixtures for any new API calls in `tests/`
- Update `config/amr_concepts.json` rather than hardcoding terms

---

## Citation

If you use this tool in research, please cite:

```
@software{amr_researcher_profiles,
  author = {Nguyen, Khoi Quan},
  title  = {AMR Researcher Profiles: A Snowball Sampling Framework for AMR Research Networks},
  year   = {2025},
  url    = {https://github.com/YOUR_USERNAME/amr-researcher-profiles}
}
```

---

## License

MIT
