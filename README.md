[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.21230851.svg)](https://doi.org/10.5281/zenodo.21230851)

> **Repository (GitHub):** https://github.com/haruki00430/ndb-premodel-audit-japan  
> **Zenodo DOI:** https://doi.org/10.5281/zenodo.21230851  
> **Reproduction:** [`REPRODUCE.md`](REPRODUCE.md) · [`CITATION.cff`](CITATION.cff)

# A Pre-Model Audit of Administrative Healthcare Data for AI-Oriented Research

## Evidence from NDB Open Data releases No.1–No.11

**論文タイトル（日本語）**: 行政医療データの AI 利用前監査——NDB オープンデータ第 1 回〜第 11 回を用いた実証的検討

**Manuscript status**: Submitted to *International Journal of Medical Informatics* (Elsevier) — 2026-07-09  
**Repository:** https://github.com/haruki00430/ndb-premodel-audit-japan

---

## Abstract / 研究概要

Administrative healthcare data are increasingly used for AI-oriented research, but their readiness for such use is seldom evaluated before model development. This study demonstrates a pre-model audit of NDB Open Data releases No.1 to No.11 — Japan's publicly released national administrative healthcare database — to assess whether selected diabetes/metabolic and dental/oral indicators can support a reproducible prefecture-year panel across releases.

Full-panel extraction yielded 146,376 long-format records (47 prefectures × 11 releases). Nine selected diabetes/metabolic mean-value indicators achieved 100% prefecture coverage across all 11 releases with zero suppressed cells. Dental/oral disease-count indicators covered 10 of 11 releases at the prefecture level, but cell-level suppression ranged from 19% to 47% depending on release year. Nine undocumented structural changes across releases No.1–No.11 required bespoke extraction logic and would silently break standard automated pipelines.

The results suggest that AI readiness is a study-specific property of administrative data measurement conditions, not a generic property of the data source, and that a pre-model audit can help distinguish file availability from study-ready data before model development begins.

---

行政医療データは AI 研究に広く利用されているが、モデル開発前のデータ利用可能性評価（事前監査）は行われないことが多い。本研究は NDB オープンデータ第 1〜11 回を対象に、糖尿病・メタボ指標および歯科傷病指標が都道府県×年度の再現可能なパネルを支持できるかを検討した。全パネル抽出では 146,376 件のレコード（47 都道府県 × 11 リリース）を生成した。糖尿病/メタボ系 9 指標は全リリースで都道府県カバレッジ 100%・伏字ゼロを達成した。歯科傷病指標は 10/11 リリースで都道府県カバレッジ 100% を達成したが、セル単位の伏字率は 19〜47% であった。11 リリース全体で 9 件の無文書化構造変化が検出された。これらは標準的な自動処理パイプラインでサイレント失敗を引き起こすタイプの問題であり、行政データの AI 利用においては事前監査が有効であることを示す。

---

## Submission / 投稿情報

| Item | Content |
|------|---------|
| Journal | [*International Journal of Medical Informatics*](https://www.sciencedirect.com/journal/international-journal-of-medical-informatics) (Elsevier) |
| Article type | Original Research Article |
| Submitted | 2026-07-09 |
| Status | Submitted |
| Prior submission | Journal of Biomedical Informatics (JBI-26-2457; desk rejection without peer review, 2026-07-08) |

---

## Repository Structure / ディレクトリ構造

```
ndb-premodel-audit-japan/
├── README.md                   # This file
├── CITATION.cff                # Citation metadata
├── REPRODUCE.md                # Reproduction instructions
├── LICENSE                     # MIT
├── scripts/
│   ├── 01_build_file_inventory.py       # File inventory (feasibility phase)
│   ├── 02_identify_candidate_items.py   # Indicator candidate identification
│   ├── 03_extract_prototype_data.py     # Prototype extraction (3 releases)
│   ├── 04_unit_title_audit.py           # HbA1C unit/label audit across 11 releases
│   ├── 05_full_panel_extraction.py      # Full 11-release panel extraction
│   ├── 06_coverage_profiles.py          # Coverage matrix + missing-state profiles
│   └── 07_figures.py                    # Figure generation (heatmap + bar chart)
├── data/
│   └── processed/
│       └── ndb_prefecture_year_full_panel.csv   # Full panel (146,376 records)
├── tables/
│   ├── coverage_matrix.csv              # Indicator × fiscal_year coverage
│   ├── missing_suppression_profile.csv  # Missing-state distribution
│   └── sensitivity_summary.csv          # Sensitivity scenarios (A/B/C)
├── metadata/
│   └── unit_title_audit.csv             # HbA1C label audit per release
└── figures/
    ├── temporal_coverage.png            # Heatmap: coverage by indicator × year
    └── domain_missing_profile.png       # Stacked bar: missing-state by indicator
```

---

## Key Findings / 主な発見

| Finding | Description |
|---------|-------------|
| **R1** | 9 diabetes/metabolic indicators: 100% coverage, 0% suppression across all 11 releases |
| **R2** | Dental disease-count panel: 10/11 releases; suppression 47% (FY2014) → 19% (FY2022–) |
| **R3** | HbA1C NGSP unit notation dropped after No.5 without documentation |
| **R4** | No.8/FY2021 dental data used procedure counts (算定回数) instead of disease counts |
| **R5** | 9 undocumented structural changes across 11 releases; all required bespoke handling |

---

## Missing-State Vocabulary

This study uses a controlled vocabulary for missing states. Suppressed cells are **never** treated as zero.

| missing_state | Meaning |
|---------------|---------|
| `observed` | Numeric value present |
| `suppressed` | Cell withheld because count < 10 (NDB disclosure control) |
| `metric_change` | Metric definition changed; cross-year comparison not valid |
| `prefecture_unknown` | Geography unassigned; excluded from main panel |
| `unpublished` | Release did not publish this indicator |
| `parse_error` | File read error |
| `not_applicable` | Structural placeholder (e.g., total row) |

---

## Data Source / データソース

All source data: **NDB Open Data** (National Database of Health Insurance Claims and Specific Health Checkups of Japan), releases No.1–No.11.  
Published by the Ministry of Health, Labour and Welfare, Japan.  
> https://www.mhlw.go.jp/stf/seisakunitsuite/bunya/0000177182.html

Source files were treated as **read-only**. No individual-level data were used.  
No suppressed cells were imputed. No AI model was fitted.

---

## How to Cite / 引用

If you use the code or data in this repository, please cite:

```
Saito H, Ohira T. A Pre-Model Audit of Administrative Healthcare Data for
AI-Oriented Research: Evidence from NDB Open Data releases No.1-No.11.
International Journal of Medical Informatics. 2026. [Submitted]
https://doi.org/10.5281/zenodo.21230851
```

See [`CITATION.cff`](CITATION.cff) for machine-readable citation metadata.

---

## License

Code: [MIT License](LICENSE)  
Derived data: The panel data in `data/processed/` is derived from publicly available NDB Open Data. Source data are subject to the terms of the Ministry of Health, Labour and Welfare, Japan.
