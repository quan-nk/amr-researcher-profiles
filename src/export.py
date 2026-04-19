"""Serialize SnowballResult to CSV and JSON."""

import json
from collections import Counter, deque
from datetime import datetime
from pathlib import Path

import pandas as pd


def save(result, output_dir: str | Path, seed_id: str, depth: int) -> Path:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    pd.DataFrame(result.authors.values()).to_csv(out / "authors.csv", index=False)
    pd.DataFrame(result.papers.values()).to_csv(out / "papers.csv", index=False)

    edge_counts = Counter((a, b) for a, b, _ in result.edges)
    edges_df = pd.DataFrame(
        [{"author_a_id": a, "author_b_id": b, "shared_paper_count": n}
         for (a, b), n in edge_counts.items()]
    )
    edges_df.to_csv(out / "network.csv", index=False)

    meta = {
        "seed_author_id": seed_id,
        "depth": depth,
        "timestamp": datetime.utcnow().isoformat(),
        "total_authors": len(result.authors),
        "total_amr_papers": len(result.papers),
        "total_edges": len(edge_counts),
    }
    (out / "run_meta.json").write_text(json.dumps(meta, indent=2))

    return out


def save_checkpoint(result, visited: set, queue: deque, out_dir: str | Path) -> None:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    pd.DataFrame(result.authors.values()).to_csv(out / "authors.csv", index=False)
    pd.DataFrame(result.papers.values()).to_csv(out / "papers.csv", index=False)

    (out / "_ckpt_visited.json").write_text(json.dumps(list(visited)))
    (out / "_ckpt_queue.json").write_text(json.dumps([list(item) for item in queue]))
    (out / "_ckpt_edges.json").write_text(json.dumps(result.edges))


def load_checkpoint(out_dir: str | Path):
    """Return (SnowballResult, visited, queue) if a checkpoint exists, else None."""
    from .snowball import SnowballResult  # local import avoids circular dependency

    out = Path(out_dir)
    if not (out / "_ckpt_visited.json").exists():
        return None

    visited = set(json.loads((out / "_ckpt_visited.json").read_text()))
    queue = deque(tuple(x) for x in json.loads((out / "_ckpt_queue.json").read_text()))

    authors, papers, edges = {}, {}, []
    if (out / "authors.csv").exists():
        for row in pd.read_csv(out / "authors.csv").to_dict("records"):
            authors[row["id"]] = row
    if (out / "papers.csv").exists():
        for row in pd.read_csv(out / "papers.csv").to_dict("records"):
            papers[row["id"]] = row
    if (out / "_ckpt_edges.json").exists():
        edges = [tuple(x) for x in json.loads((out / "_ckpt_edges.json").read_text())]

    return SnowballResult(authors=authors, papers=papers, edges=edges), visited, queue
