#!/usr/bin/env bash
# Fetch the two public substrates and verify checksums (see data/PROVENANCE.md).
set -euo pipefail
cd "$(dirname "$0")/.."
curl -sL -o data/date_synthetic.csv \
  "https://raw.githubusercontent.com/Roytsai27/Dual-Attentive-Tree-aware-Embedding/master/data/synthetic-imports-declarations.csv"
curl -sL -o data/ctgan_declarations.csv \
  "https://raw.githubusercontent.com/Seondong/Customs-Declaration-Datasets/master/data/df_syn_eng.csv"
sha256sum -c - <<'SUMS'
e89c97727f2193f328759cfbc9c4a9ad1a93886c1bd6d3af8e5eded2afee67c6  data/date_synthetic.csv
cb6984e165994f7c92958113b9a3c86a5f5f6891ad23192fc23f39301b537767  data/ctgan_declarations.csv
SUMS
echo "substrates fetched and verified"
