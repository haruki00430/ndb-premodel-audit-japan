# DATA_SOURCES.md — NDB Open Data Source Details

This file documents the primary data sources used in this project:
the Ministry of Health, Labour and Welfare (MHLW) NDB Open Data
(National Database of Health Insurance Claims and Specific Health Checkups of Japan).

---

## Primary Data Source

| Item | Value |
|------|-------|
| **Dataset name** | NDB オープンデータ（NDB Open Data） |
| **Provider** | Ministry of Health, Labour and Welfare, Japan（厚生労働省） |
| **Coverage** | FY2013–FY2024（releases No.1–No.11） |
| **Access** | Public; freely downloadable from MHLW website |
| **File count** | 3,137 Excel files across 11 releases |
| **Total size** | ~15 GB (all 11 releases combined) |
| **Local path** | `02_Data/raw/NDB_OpenData/` (read-only; not tracked by Git) |

---

## Release Overview

| Release | Receipt FY | Checkup FY | Note |
|---------|-----------|-----------|------|
| No.1  | FY2014 | FY2013 | Questionnaire data absent; oldest release |
| No.2  | FY2015 | FY2014 | |
| No.3  | FY2016 | FY2015 | |
| No.4  | FY2017 | FY2016 | |
| No.5  | FY2018 | FY2017 | |
| No.6  | FY2019 | FY2018 | Secondary medical area (二次医療圏) data added |
| No.7  | FY2020 | FY2019 | |
| No.8  | FY2021 | FY2020 | Dental metric changed: 傷病件数 → 算定回数 |
| No.9  | FY2022 | FY2021 | |
| No.10 | FY2023 | FY2022 | Folder structure reorganized; public-fee exclusion made default |
| No.11 | FY2024 | FY2023 | Most recent release |

---

## Folder Structure Within Each Release

```
02_Data/raw/NDB_OpenData/
└── No.{1-11}/
    ├── 01_医科診療行為（患者数）/      Medical acts (patient count)
    ├── 01_医科診療行為（算定回数）/    Medical acts (procedure count)
    ├── 02_歯科診療行為（患者数）/      Dental acts (patient count)
    ├── 02_歯科診療行為（算定回数）/    Dental acts (procedure count)
    ├── 03_調剤行為（患者数）/          Dispensing (patient count)
    ├── 03_調剤行為（算定回数）/        Dispensing (procedure count)
    ├── 04_歯科傷病/                    Dental diseases ← used in this project
    ├── 05_処方薬/                      Prescription drugs
    ├── 06_特定保険医療材料/            Medical materials
    ├── 07_特定健診 検査/               Specific health checkup exams ← used
    └── 07_特定健診 質問票/             Specific health checkup questionnaire
```

---

## Source Files Used in Extraction

### Domain: Diabetes / Metabolic (Script 05)

The primary source for 9 metabolic indicators is the **"各項目の平均値 都道府県別"** file
(prefecture-level mean values of all checkup items), located under `07_特定健診 検査/`.

**File naming patterns by release:**

| Release | File pattern example |
|---------|---------------------|
| No.1–5  | `各項目の平均値_受診時年齢別_都道府県別.xlsx` |
| No.6–9  | `（※1）各項目の平均値_都道府県別性年齢階級別.xlsx` |
| No.10–11 | `01_公費レセプトを含まないデータ/各項目の平均値_都道府県別性年齢階級別.xlsx` |

**Excel internal structure:**

```
Row 0: Title (fiscal year, data description)
Row 1: Header tier 1 (prefecture col | item col | male age groups | female age groups)
Row 2: Header tier 2 (sex label spanning)
Row 3: Header tier 3 (age group labels: 40-44, 45-49, ..., 70-74, total)
Row 4: Header tier 4 (units)
Row 5+: Data (prefecture × item, one row per item per prefecture)
```

**Important parsing notes:**
- Prefecture name column (col 0): populated only in the first row of each prefecture; subsequent rows are blank → requires `ffill()` (forward fill) before filtering
- Item name column (col 1): may contain "(NGSP)[%]" suffix (No.1–5) or be label-only (No.6–11)
- LDL/HDL columns in No.6–11 use full-width (double-byte) ASCII: "ＬＤＬ", "ＨＤＬ" → requires NFKC normalization

### Domain: Dental / Oral (Script 05)

The primary source for dental disease counts is the **"歯科傷病 都道府県別"** file,
located under `04_歯科傷病/`.

**File naming patterns:**

| Release | File pattern example |
|---------|---------------------|
| No.1–7, 9 | `歯科傷病_傷病件数_都道府県別.xlsx` (disease episode count) |
| No.8     | `歯科傷病_算定回数_都道府県別.xlsx` (procedure count — METRIC CHANGE) |
| No.10–11 | `01_公費レセプトを含まないデータ/歯科傷病_傷病件数_都道府県別.xlsx` |

**Excel internal structure:**

```
Row 0: Title (fiscal year)
Row 1: (blank)
Row 2: Header tier 1 (disease group | disease code | disease name | total | 01北海道 | ...)
Row 3: Header tier 2 (NaN | NaN | NaN | NaN | 北海道 | 青森 | ...)
Row 4+: Data (disease code rows × prefecture columns)
```

**Important parsing note:**
- Disease group column: populated only in first row of each disease group → requires `ffill()` before filtering
- No.8: metric changed from 傷病件数 to 算定回数 → these records are coded `metric_change` and excluded from main analyses

---

## Suppression Rule

NDB Open Data applies a **small-count suppression rule**: cells where the count is fewer than 10
are masked and displayed as "－" (full-width minus sign) in the Excel file.

These cells are coded `suppressed` in this project's panel, never as zero or missing.
**Do not impute suppressed cells unless explicitly requested in a sensitivity analysis.**

Suppression rates vary by domain:
- Diabetes/metabolic indicators: ~0% suppressed (population-level mean values, not counts)
- Dental disease counts: ~17.6% suppressed (prefecture × disease code combinations with <10 cases)

---

## Citation

Ministry of Health, Labour and Welfare. NDB Open Data: National Database of Health Insurance Claims and Specific Health Checkups of Japan. Available from: https://www.mhlw.go.jp/stf/seisakunitsuite/bunya/0000177221_00012.html (Accessed 2026-07-07).

---

## Data Security

Raw NDB data files are stored locally at `02_Data/raw/NDB_OpenData/` and are:
- **Read-only**: never modified by any script in this project
- **Not tracked by Git**: excluded via `.gitignore`
- **Not transmitted to AI**: actual cell values are never sent to external AI services
- **Not uploaded to GitHub**: only derived tables and analysis code are published
