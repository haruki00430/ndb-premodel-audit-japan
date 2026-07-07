# Reproduction Guide

This document describes how to reproduce all outputs of the pre-model audit
from the publicly available NDB Open Data source files.

## Prerequisites

### 1. NDB Open Data source files

Download releases No.1–No.11 from the Ministry of Health, Labour and Welfare, Japan:
> https://www.mhlw.go.jp/stf/seisakunitsuite/bunya/0000177182.html

Place the extracted folders at:
```
02_Data/raw/NDB_OpenData/No.1/
02_Data/raw/NDB_OpenData/No.2/
...
02_Data/raw/NDB_OpenData/No.11/
```

**The raw files are read-only inputs. Do not modify them.**

### 2. Python environment

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install pandas numpy matplotlib seaborn geopandas openpyxl unicodedata2
```

Or, if running from within NDB_Research_Hub:
```bash
pip install -e ../../  # installs ndb_library from src/
```

## Execution Order

Run the four scripts in order from the repository root:

```bash
# Step 1: Audit HbA1C unit labels across all 11 releases
python scripts/04_unit_title_audit.py

# Step 2: Extract the full prefecture-year panel (146,376 records)
python scripts/05_full_panel_extraction.py

# Step 3: Build coverage matrix, missing-state profile, sensitivity table
python scripts/06_coverage_profiles.py

# Step 4: Generate figures (temporal coverage heatmap + domain missing profile)
python scripts/07_figures.py
```

## Expected Outputs

| Script | Output file | Expected result |
|--------|-------------|-----------------|
| `04_unit_title_audit.py` | `metadata/unit_title_audit.csv` | 11 rows; 0 JDS labels |
| `05_full_panel_extraction.py` | `data/processed/ndb_prefecture_year_full_panel.csv` | 146,376 records |
| `06_coverage_profiles.py` | `tables/coverage_matrix.csv` | 110 rows |
| `06_coverage_profiles.py` | `tables/missing_suppression_profile.csv` | 1,611 rows |
| `06_coverage_profiles.py` | `tables/sensitivity_summary.csv` | 12 rows |
| `07_figures.py` | `figures/temporal_coverage.png` | heatmap, 300 dpi |
| `07_figures.py` | `figures/domain_missing_profile.png` | bar chart, 300 dpi |

### Key validation checks

```
Total records:          146,376
Observed (81.8%):       119,733
Suppressed (17.6%):      25,732
Prefecture_unknown (0.6%):   864
Metric_change (0.03%):        47

Metabolic indicators:  9/9 × 11/11 releases × 47/47 prefectures (100%)
Suppression in metabolic domain: 0 cells
Dental releases covered: 10/11 (No.8/FY2021 = metric_change)
```

## Pre-computed Outputs (included in this repository)

The derived panel and tables are included for reference:
- `data/processed/ndb_prefecture_year_full_panel.csv`
- `tables/coverage_matrix.csv`
- `tables/missing_suppression_profile.csv`
- `tables/sensitivity_summary.csv`
- `metadata/unit_title_audit.csv`
- `figures/temporal_coverage.png`
- `figures/domain_missing_profile.png`

These files were generated from NDB Open Data (public source). No individual-level data,
no suppressed cells were imputed, and no AI model was fitted.

## Notes on Structural Changes

Scripts handle the following undocumented structural changes across releases:

| Change | Releases | Handling |
|--------|----------|----------|
| HbA1C filename case (`HbA1C` vs `HbA1c`) | Mixed across all | Case-insensitive "HbA1" pattern |
| LDL/HDL label abbreviated (full → `ＬＤＬ`/`ＨＤＬ`) | No.6–11 | NFKC normalization + bidirectional match |
| HbA1C NGSP notation dropped | No.6–11 | Unit audit confirms NGSP by policy |
| Dental metric change (傷病件数 → 算定回数) | No.8 only | `metric_change` flag |
| Folder restructuring (01_公費... subfolder added) | No.10–11 | Priority-based path selection |
