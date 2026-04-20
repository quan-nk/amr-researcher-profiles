"""Generate a self-contained HTML summary report from top100_authors.csv and top300_papers.csv."""

from __future__ import annotations
import argparse
import os
import json
import textwrap

import networkx as nx
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio


DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
SKIP_SEEDS = {"ben_cooper", "20260418T234105"}


# ── data loading ─────────────────────────────────────────────────────────────

def load_data(data_dir: str):
    authors = pd.read_csv(os.path.join(data_dir, "top100_authors.csv"))
    papers = pd.read_csv(os.path.join(data_dir, "top300_papers.csv"))

    edges_all: list[tuple[str, str, int]] = []
    processed_dir = os.path.join(data_dir, "processed")
    for seed in os.listdir(processed_dir):
        if seed in SKIP_SEEDS:
            continue
        net_path = os.path.join(processed_dir, seed, "network.csv")
        if not os.path.exists(net_path):
            continue
        try:
            net = pd.read_csv(net_path)
            for _, row in net.iterrows():
                edges_all.append((row["author_a_id"], row["author_b_id"], int(row["shared_paper_count"])))
        except Exception:
            continue

    return authors, papers, edges_all


# ── network graph ─────────────────────────────────────────────────────────────

def build_network_figure(authors: pd.DataFrame, edges_all: list) -> str:
    top50 = set(authors.head(50)["id"])
    author_meta = authors.set_index("id").to_dict("index")

    G = nx.Graph()
    for aid in top50:
        G.add_node(aid)
    edge_weights: dict[tuple, int] = {}
    for a, b, w in edges_all:
        if a in top50 and b in top50:
            key = (min(a, b), max(a, b))
            edge_weights[key] = edge_weights.get(key, 0) + w
    for (a, b), w in edge_weights.items():
        G.add_edge(a, b, weight=w)

    pos = nx.spring_layout(G, k=2.5, seed=42, weight="weight")

    # seed appearance color scale (1–14)
    def seed_color(n):
        meta = author_meta.get(n, {})
        s = meta.get("seed_appearances", 1)
        # map 1-14 to blue-orange
        t = min((s - 1) / 13, 1.0)
        r = int(255 * t)
        g = int(140 * (1 - t) + 80 * t)
        b = int(255 * (1 - t))
        return f"rgb({r},{g},{b})"

    edge_traces = []
    for (a, b), w in edge_weights.items():
        if a not in pos or b not in pos:
            continue
        x0, y0 = pos[a]
        x1, y1 = pos[b]
        edge_traces.append(go.Scatter(
            x=[x0, x1, None], y=[y0, y1, None],
            mode="lines",
            line=dict(width=max(0.5, min(w * 0.3, 3)), color="rgba(150,150,150,0.35)"),
            hoverinfo="none",
            showlegend=False,
        ))

    node_x, node_y, node_text, node_hover, node_size, node_color = [], [], [], [], [], []
    for n in G.nodes():
        if n not in pos:
            continue
        meta = author_meta.get(n, {})
        x, y = pos[n]
        node_x.append(x)
        node_y.append(y)
        name = meta.get("name", n.split("/")[-1])
        node_text.append(name)
        h = meta.get("h_index") or 0
        s = meta.get("seed_appearances", 1)
        amr = meta.get("amr_paper_count", 0)
        inst = meta.get("institution") or "unknown"
        node_hover.append(
            f"<b>{name}</b><br>h-index: {h}<br>AMR papers: {amr}<br>"
            f"Seed appearances: {s}<br>Institution: {inst}"
        )
        node_size.append(max(8, min(h ** 0.55, 30)))
        node_color.append(seed_color(n))

    node_trace = go.Scatter(
        x=node_x, y=node_y,
        mode="markers+text",
        text=node_text,
        textposition="top center",
        textfont=dict(size=8, color="#333"),
        hovertext=node_hover,
        hoverinfo="text",
        marker=dict(
            size=node_size,
            color=node_color,
            line=dict(width=1, color="white"),
        ),
        showlegend=False,
    )

    fig = go.Figure(
        data=edge_traces + [node_trace],
        layout=go.Layout(
            title=dict(text="Co-authorship network — top 50 authors", font=dict(size=14)),
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            hovermode="closest",
            height=620,
            margin=dict(l=10, r=10, t=40, b=10),
            plot_bgcolor="#fafafa",
            paper_bgcolor="#fafafa",
            annotations=[dict(
                x=0.5, y=-0.02, xref="paper", yref="paper",
                text="Node size ∝ h-index &nbsp;|&nbsp; Node color: blue = fewer seeds, orange = more seeds",
                showarrow=False, font=dict(size=10, color="#666"),
            )],
        ),
    )
    return pio.to_html(fig, full_html=False, include_plotlyjs=False, config={"responsive": True})


# ── seed heatmap ──────────────────────────────────────────────────────────────

def build_heatmap_figure(authors: pd.DataFrame, data_dir: str) -> str:
    processed_dir = os.path.join(data_dir, "processed")
    top20_ids = list(authors.head(20)["id"])
    top20_names = list(authors.head(20)["name"])

    seed_dirs = [s for s in os.listdir(processed_dir)
                 if s not in SKIP_SEEDS
                 and os.path.exists(os.path.join(processed_dir, s, "authors.csv"))]

    presence: dict[str, dict[str, bool]] = {aid: {} for aid in top20_ids}
    for seed in seed_dirs:
        try:
            df = pd.read_csv(os.path.join(processed_dir, seed, "authors.csv"))
            found = set(df["id"].tolist())
            for aid in top20_ids:
                presence[aid][seed] = aid in found
        except Exception:
            continue

    seeds_sorted = sorted(seed_dirs)
    z = [[1 if presence[aid].get(s, False) else 0 for s in seeds_sorted] for aid in top20_ids]

    seed_labels = [s.replace("_", " ").title() for s in seeds_sorted]
    author_labels = [n[:28] for n in top20_names]

    fig = go.Figure(go.Heatmap(
        z=z,
        x=seed_labels,
        y=author_labels,
        colorscale=[[0, "#f0f4ff"], [1, "#2563eb"]],
        showscale=False,
        xgap=2, ygap=2,
        hovertemplate="Author: %{y}<br>Seed: %{x}<br>Found: %{z}<extra></extra>",
    ))
    fig.update_layout(
        title=dict(text="Top 20 authors × seed coverage", font=dict(size=14)),
        xaxis=dict(tickangle=-40, tickfont=dict(size=9)),
        yaxis=dict(tickfont=dict(size=9), autorange="reversed"),
        height=520,
        margin=dict(l=160, r=10, t=40, b=120),
        plot_bgcolor="#fafafa",
        paper_bgcolor="#fafafa",
    )
    return pio.to_html(fig, full_html=False, include_plotlyjs=False, config={"responsive": True})


# ── HTML assembly ─────────────────────────────────────────────────────────────

def _seed_badge(n: int) -> str:
    intensity = min(n / 14, 1.0)
    r = int(37 + (234 - 37) * intensity)
    g = int(99 + (88 - 99) * intensity)
    b = int(235 + (36 - 235) * intensity)
    text_color = "white" if intensity > 0.4 else "#1e3a5f"
    return (f'<span style="background:rgb({r},{g},{b});color:{text_color};'
            f'padding:2px 7px;border-radius:10px;font-size:11px;font-weight:600">{n}</span>')


def authors_table_html(authors: pd.DataFrame) -> str:
    rows = []
    for _, r in authors.iterrows():
        inst = r["institution"] if pd.notna(r.get("institution")) else "—"
        badge = _seed_badge(int(r["seed_appearances"]))
        rows.append(
            f"<tr>"
            f"<td>{int(r['rank'])}</td>"
            f"<td><b>{r['name']}</b></td>"
            f"<td>{inst}</td>"
            f"<td>{int(r['h_index']) if pd.notna(r['h_index']) else '—'}</td>"
            f"<td>{int(r['amr_paper_count'])}</td>"
            f"<td>{badge}</td>"
            f"<td>{r['score']:.1f}</td>"
            f"</tr>"
        )
    body = "\n".join(rows)
    return f"""
<table id="authors-tbl" class="data-tbl">
<thead><tr>
  <th onclick="sortTable('authors-tbl',0,'n')"># <span class="sort-icon">⇅</span></th>
  <th onclick="sortTable('authors-tbl',1,'s')">Name <span class="sort-icon">⇅</span></th>
  <th onclick="sortTable('authors-tbl',2,'s')">Institution <span class="sort-icon">⇅</span></th>
  <th onclick="sortTable('authors-tbl',3,'n')">h-index <span class="sort-icon">⇅</span></th>
  <th onclick="sortTable('authors-tbl',4,'n')">AMR papers <span class="sort-icon">⇅</span></th>
  <th onclick="sortTable('authors-tbl',5,'n')">Seeds <span class="sort-icon">⇅</span></th>
  <th onclick="sortTable('authors-tbl',6,'n')">Score <span class="sort-icon">⇅</span></th>
</tr></thead>
<tbody>{body}</tbody>
</table>"""


def papers_table_html(papers: pd.DataFrame) -> str:
    rows = []
    for _, r in papers.iterrows():
        doi = r.get("doi", "")
        title_cell = (f'<a href="{doi}" target="_blank">{r["title"]}</a>'
                      if pd.notna(doi) and doi else r["title"])
        journal = r["journal"] if pd.notna(r.get("journal")) else "—"
        badge = _seed_badge(int(r["seed_appearances"]))
        rows.append(
            f"<tr>"
            f"<td>{int(r['rank'])}</td>"
            f"<td class='title-cell'>{title_cell}</td>"
            f"<td>{int(r['year']) if pd.notna(r.get('year')) else '—'}</td>"
            f"<td>{journal}</td>"
            f"<td>{badge}</td>"
            f"</tr>"
        )
    body = "\n".join(rows)
    return f"""
<table id="papers-tbl" class="data-tbl">
<thead><tr>
  <th onclick="sortTable('papers-tbl',0,'n')"># <span class="sort-icon">⇅</span></th>
  <th>Title</th>
  <th onclick="sortTable('papers-tbl',2,'n')">Year <span class="sort-icon">⇅</span></th>
  <th onclick="sortTable('papers-tbl',3,'s')">Journal <span class="sort-icon">⇅</span></th>
  <th onclick="sortTable('papers-tbl',4,'n')">Seeds <span class="sort-icon">⇅</span></th>
</tr></thead>
<tbody>{body}</tbody>
</table>"""


CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
       background: #f3f4f6; color: #1f2937; }
.page { max-width: 1280px; margin: 0 auto; padding: 24px 20px; }
h1 { font-size: 1.6rem; font-weight: 700; margin-bottom: 4px; }
.subtitle { color: #6b7280; font-size: 0.9rem; margin-bottom: 24px; }
h2 { font-size: 1.1rem; font-weight: 600; margin-bottom: 12px; color: #1e3a5f; }

/* stat cards */
.cards { display: flex; gap: 14px; margin-bottom: 28px; flex-wrap: wrap; }
.card { background: white; border-radius: 10px; padding: 18px 22px;
        flex: 1; min-width: 140px; box-shadow: 0 1px 4px rgba(0,0,0,.08); }
.card .num { font-size: 2rem; font-weight: 700; color: #2563eb; }
.card .label { font-size: 0.8rem; color: #6b7280; margin-top: 2px; }

/* panels */
.panel { background: white; border-radius: 10px; padding: 20px 22px;
         margin-bottom: 24px; box-shadow: 0 1px 4px rgba(0,0,0,.08); }
.two-col { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
@media(max-width: 860px) { .two-col { grid-template-columns: 1fr; } }

/* search */
.search-wrap { margin-bottom: 10px; }
.search-wrap input { padding: 6px 12px; border: 1px solid #d1d5db;
  border-radius: 6px; font-size: 0.85rem; width: 260px; }

/* tables */
.data-tbl { width: 100%; border-collapse: collapse; font-size: 0.82rem; }
.data-tbl thead th { background: #1e3a5f; color: white; padding: 8px 10px;
  text-align: left; cursor: pointer; white-space: nowrap; user-select: none; }
.data-tbl thead th:hover { background: #2563eb; }
.sort-icon { opacity: 0.5; font-size: 10px; }
.data-tbl tbody tr:nth-child(even) { background: #f8fafc; }
.data-tbl tbody tr:hover { background: #eff6ff; }
.data-tbl td { padding: 7px 10px; vertical-align: top; }
.data-tbl td:first-child { color: #9ca3af; font-size: 0.75rem; width: 32px; }
.title-cell { max-width: 520px; }
.title-cell a { color: #2563eb; text-decoration: none; }
.title-cell a:hover { text-decoration: underline; }

/* table wrapper scroll */
.tbl-wrap { overflow-x: auto; }
"""

JS = r"""
function sortTable(id, col, type) {
  const tbl = document.getElementById(id);
  const tbody = tbl.querySelector('tbody');
  const rows = Array.from(tbody.querySelectorAll('tr'));
  const th = tbl.querySelectorAll('th')[col];
  const asc = th.dataset.sort !== 'asc';
  tbl.querySelectorAll('th').forEach(h => h.dataset.sort = '');
  th.dataset.sort = asc ? 'asc' : 'desc';

  const val = td => {
    const span = td.querySelector('span');
    const t = span ? span.textContent : td.textContent;
    return type === 'n' ? (parseFloat(t) || 0) : t.toLowerCase();
  };
  rows.sort((a, b) => {
    const va = val(a.cells[col]), vb = val(b.cells[col]);
    const cmp = type === 'n' ? va - vb : va.localeCompare(vb);
    return asc ? cmp : -cmp;
  });
  rows.forEach(r => tbody.appendChild(r));
}

function filterTable(inputId, tableId) {
  const q = document.getElementById(inputId).value.toLowerCase();
  const tbl = document.getElementById(tableId);
  tbl.querySelectorAll('tbody tr').forEach(row => {
    row.style.display = row.textContent.toLowerCase().includes(q) ? '' : 'none';
  });
}
"""


def render_html(authors: pd.DataFrame, papers: pd.DataFrame,
                net_html: str, heatmap_html: str,
                n_seeds: int) -> str:
    stat_cards = f"""
<div class="cards">
  <div class="card"><div class="num">100</div><div class="label">Top authors</div></div>
  <div class="card"><div class="num">300</div><div class="label">Must-read papers</div></div>
  <div class="card"><div class="num">{n_seeds}</div><div class="label">Seeds used</div></div>
  <div class="card"><div class="num">{int(authors['h_index'].median())}</div><div class="label">Median h-index</div></div>
  <div class="card"><div class="num">{int(authors['seed_appearances'].max())}</div><div class="label">Max seed coverage</div></div>
</div>"""

    author_tbl = authors_table_html(authors)
    paper_tbl = papers_table_html(papers)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>AMR Research Network — Summary Report</title>
<script src="https://cdn.plot.ly/plotly-3.3.0.min.js"></script>
<style>{CSS}</style>
</head>
<body>
<div class="page">

<h1>AMR Research Network</h1>
<p class="subtitle">Snowball sampling from {n_seeds} seed researchers · OpenAlex · {pd.Timestamp.now().strftime('%B %Y')}</p>

{stat_cards}

<div class="two-col">
  <div class="panel">
    <h2>Co-authorship network</h2>
    {net_html}
  </div>
  <div class="panel">
    <h2>Seed coverage heatmap</h2>
    {heatmap_html}
  </div>
</div>

<div class="panel">
  <h2>Top 100 authors</h2>
  <div class="search-wrap">
    <input id="author-search" type="text" placeholder="Search name / institution…"
      oninput="filterTable('author-search','authors-tbl')">
  </div>
  <div class="tbl-wrap">
    {author_tbl}
  </div>
</div>

<div class="panel">
  <h2>Top 300 must-read papers</h2>
  <div class="search-wrap">
    <input id="paper-search" type="text" placeholder="Search title / journal…"
      oninput="filterTable('paper-search','papers-tbl')">
  </div>
  <div class="tbl-wrap">
    {paper_tbl}
  </div>
</div>

</div>
<script>{JS}</script>
</body>
</html>"""


# ── entry point ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Generate AMR network HTML report")
    parser.add_argument("--data-dir", default=DATA_DIR)
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    data_dir = os.path.abspath(args.data_dir)
    out_path = args.output or os.path.join(data_dir, "summary.html")

    print("Loading data…")
    authors, papers, edges_all = load_data(data_dir)

    processed_dir = os.path.join(data_dir, "processed")
    n_seeds = sum(
        1 for s in os.listdir(processed_dir)
        if s not in SKIP_SEEDS
        and os.path.exists(os.path.join(processed_dir, s, "authors.csv"))
    )

    print("Building network figure…")
    net_html = build_network_figure(authors, edges_all)

    print("Building heatmap figure…")
    heatmap_html = build_heatmap_figure(authors, data_dir)

    print("Assembling HTML…")
    html = render_html(authors, papers, net_html, heatmap_html, n_seeds)

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"Report saved → {out_path}")


if __name__ == "__main__":
    main()
