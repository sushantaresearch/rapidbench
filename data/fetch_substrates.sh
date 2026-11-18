#!/usr/bin/env bash
# Fetch the two public substrates used by RAPID-Bench E2 cross-substrate runs.
# S-B: DATE synthetic customs imports (Kim et al.), Seondong/Customs-Fraud-Detection
# S-C: CTGAN Korea Customs declarations (Jeong, Kim et al., arXiv:2208.02484, MIT), Seondong/Customs-Declaration-Datasets
set -euo pipefail
cd "$(dirname "$0")"
curl -L -o date_synthetic.csv \
  https://raw.githubusercontent.com/Seondong/Customs-Fraud-Detection/master/data/synthetic-imports-declarations.csv
curl -L -o ctgan_declarations.csv \
  https://raw.githubusercontent.com/Seondong/Customs-Declaration-Datasets/en/data/df_syn_eng.csv
sha256sum -c SHA256SUMS
