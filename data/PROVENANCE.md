# Substrate provenance

Downloaded 2 Jul 2026 (UTC), verbatim, no preprocessing before load time.

## S-B: DATE public synthetic customs imports
- Source: https://raw.githubusercontent.com/Roytsai27/Dual-Attentive-Tree-aware-Embedding/master/data/synthetic-imports-declarations.csv
  (repository of Kim et al., DATE, KDD 2020)
- Local file: data/date_synthetic.csv
- sha256: e89c97727f2193f328759cfbc9c4a9ad1a93886c1bd6d3af8e5eded2afee67c6
- 100,000 rows x 14 columns. Licence: per source repository.

## S-C: CTGAN-generated Korea customs declarations
- Source: https://raw.githubusercontent.com/Seondong/Customs-Declaration-Datasets/master/data/df_syn_eng.csv
  (Jeong, Kim et al., arXiv:2208.02484; MIT licence per repository)
- Local file: data/ctgan_declarations.csv
- sha256: cb6984e165994f7c92958113b9a3c86a5f5f6891ad23192fc23f39301b537767
- 54,000 rows x 22 columns; loader drops 506 non-positive mass/price rows.

Loaders: rapidbench/substrate.py (load_date_substrate, load_ctgan_substrate).
Column mapping and n/a classes are documented in the loader docstrings and
docs/E2_CROSS_SUBSTRATE.md.
