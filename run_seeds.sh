#!/usr/bin/env bash
# Snowball sampler batch runner.
# Top-10 from Ben Cooper run first (by h-index, known OpenAlex IDs).
# Then named seeds from queue (screened: h-index>=20, AMR pub in last 5 years).
# Each run capped at 500 authors, depth 2.
set -euo pipefail

DEPTH=${DEPTH:-2}
RATE=${RATE:-0.1}
MAX=${MAX:-500}
MIN_HINDEX=${MIN_HINDEX:-20}

run_by_id() {
  local id=$1 name=$2
  echo "========================================"
  echo "Processing: $name ($id)"
  echo "========================================"
  python3 -m src.cli \
    --author-id "$id" \
    --depth "$DEPTH" \
    --rate-limit "$RATE" \
    --max-authors "$MAX" \
    --min-hindex "$MIN_HINDEX" \
    --screen \
    --output "data/processed/$(echo "$name" | tr ' ' '_' | tr '[:upper:]' '[:lower:]')"
}

run_by_name() {
  local name=$1
  echo "========================================"
  echo "Processing: $name"
  echo "========================================"
  python3 -m src.cli \
    --author "$name" \
    --depth "$DEPTH" \
    --rate-limit "$RATE" \
    --max-authors "$MAX" \
    --min-hindex "$MIN_HINDEX" \
    --screen \
    --auto-select \
    --output "data/processed/$(echo "$name" | tr ' ' '_' | tr '[:upper:]' '[:lower:]')"
}

# --- Top 10 from Ben Cooper (depth-1/2 co-authors, ranked by h-index) ---
run_by_id "https://openalex.org/A5102733391" "Christopher J L Murray"
run_by_id "https://openalex.org/A5031889135" "Simon I Hay"
run_by_id "https://openalex.org/A5084217335" "Nicholas J White"
run_by_id "https://openalex.org/A5084268602" "Julian Parkhill"
run_by_id "https://openalex.org/A5066530115" "Robert E W Hancock"
run_by_id "https://openalex.org/A5100434325" "Yong-Guan Zhu"
run_by_id "https://openalex.org/A5115010691" "Gordon Dougan"
run_by_id "https://openalex.org/A5011259455" "Mohsen Naghavi"
run_by_id "https://openalex.org/A5078360219" "Jeremy Farrar"
run_by_id "https://openalex.org/A5114377516" "François Nosten"

# --- Named queue (screened: h>=20, AMR pub last 5 years) ---
run_by_name "Poojan Shrestha"
run_by_name "Joanna Coast"
run_by_name "Raymond Oppong"
run_by_name "Nga Do Thi Thuy"
run_by_name "Tuangrat Phodha"
run_by_name "Olivier Celhay"
run_by_name "Philippe J Guerin"
run_by_name "Heiman Wertheim"
run_by_name "Yoel Lubell"
run_by_name "Sonia Lewycka"

echo "All seeds processed."
