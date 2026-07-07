# DATA_SCHEMA.md — Full Panel CSV Variable Definitions

This file documents every column in `data/processed/ndb_prefecture_year_full_panel.csv`,
the primary analytical output of Script 05 (`05_full_panel_extraction.py`).

**Records**: 146,376 rows  
**Encoding**: UTF-8 with BOM (utf-8-sig)  
**Unit of observation**: one cell = one (prefecture × fiscal year × sex × age group × indicator) combination

---

## Column Definitions

| Column | Type | Values / Range | Description |
|--------|------|----------------|-------------|
| `release_no` | int | 1–11 | NDB Open Data release number (リリース番号) |
| `fiscal_year` | int | 2013–2024 | Fiscal year of the data. For metabolic indicators = specific health checkup fiscal year; for dental = claims fiscal year |
| `data_year_type` | str | `checkup_fy`, `claims_fy` | Indicates whether `fiscal_year` refers to a specific health checkup year or a claims year |
| `domain` | str | `diabetes_metabolic`, `dental_oral` | Analytical domain of the indicator |
| `indicator_name` | str | See below | Canonical indicator name (English) |
| `prefecture_code` | str | `01`–`47`, `XX` | JIS X 0401 two-digit prefecture code; `XX` = unmatched (prefecture_unknown state) |
| `prefecture_name` | str | e.g., `北海道`, `沖縄県` | Prefecture name in Japanese |
| `sex` | str | `male`, `female` | Sex stratum |
| `age_group` | str | `40-44`, `45-49`, `50-54`, `55-59`, `60-64`, `65-69`, `70-74`, `total` | Age stratum (5-year bands for metabolic; `total` = all ages combined) |
| `value` | float \| empty | numeric or blank | Observed numeric value. Empty if `missing_state` ≠ `observed` |
| `missing_state` | str | See vocabulary below | Classification of the data availability state for this cell |
| `source_file` | str | filename string | Name of the source Excel file |
| `source_subdir` | str | directory string | Subdirectory path within the NDB release folder |

---

## Indicator Names (`indicator_name`)

### Domain: `diabetes_metabolic`

| `indicator_name` | Japanese name | Unit | Source |
|-----------------|---------------|------|--------|
| `HbA1C` | HbA1c（グリコヘモグロビン） | % (NGSP) | 特定健診検査 — 各項目の平均値 |
| `fasting_glucose` | 空腹時血糖 | mg/dL | 特定健診検査 — 各項目の平均値 |
| `BMI` | BMI（体格指数） | kg/m² | 特定健診検査 — 各項目の平均値 |
| `waist_circumference` | 腹囲 | cm | 特定健診検査 — 各項目の平均値 |
| `systolic_BP` | 収縮期血圧 | mmHg | 特定健診検査 — 各項目の平均値 |
| `diastolic_BP` | 拡張期血圧 | mmHg | 特定健診検査 — 各項目の平均値 |
| `triglycerides` | 中性脂肪 | mg/dL | 特定健診検査 — 各項目の平均値 |
| `LDL_cholesterol` | LDLコレステロール | mg/dL | 特定健診検査 — 各項目の平均値 |
| `HDL_cholesterol` | HDLコレステロール | mg/dL | 特定健診検査 — 各項目の平均値 |

### Domain: `dental_oral`

| `indicator_name` | Japanese name | Unit | Source |
|-----------------|---------------|------|--------|
| `dental_disease_counts` | 歯科傷病件数 | 件数 | 04_歯科傷病 — 都道府県別 |

---

## Missing State Vocabulary (`missing_state`)

| Value | Meaning (EN) | 説明（JA） |
|-------|-------------|-----------|
| `observed` | Numeric value successfully extracted | 数値として正常に取得 |
| `suppressed` | Cell masked due to small count (<10); shown as "－" in Excel | 少数抑制（10件未満の場合に伏字） |
| `unpublished` | Indicator not published in this release | 当該リリースに非公表 |
| `metric_change` | Metric definition changed across releases (e.g., No.8 dental changed from 傷病件数 to 算定回数) | 指標定義の変更によりデータが比較不可 |
| `prefecture_unknown` | Prefecture name could not be matched to JIS code | 都道府県名と都道府県コードの照合失敗 |
| `parse_error` | File read error or unexpected cell format | ファイル読み込みエラーまたは不正セル形式 |
| `not_applicable` | Indicator not applicable in this context | 当該文脈では非対象 |
| `missing_unknown` | Cell is blank with no discernible reason | 空白（理由不明） |

**Important**: These states are mutually exclusive and must never be collapsed into a single generic "missing" category, as each represents a distinct data quality issue with different implications for analysis.

---

## Distribution Summary (Full Panel)

| `missing_state` | Count | % |
|----------------|-------|---|
| `observed` | 119,733 | 81.8% |
| `suppressed` | 25,732 | 17.6% |
| `unpublished` | 516 | 0.4% |
| `metric_change` | 235 | 0.2% |
| `prefecture_unknown` | 100 | 0.1% |
| `parse_error` | 60 | <0.1% |
| **Total** | **146,376** | **100%** |

---

## Notes on Specific Variables

### `fiscal_year` vs `data_year_type`

NDB Open Data mixes two fiscal year systems within each release:
- **Specific health checkup** (`checkup_fy`): data collected during checkup year
- **Claims** (`claims_fy`): data from medical claims, typically one year ahead of checkup year

Example — NDB No.10: `checkup_fy = 2022`, `claims_fy = 2023`

### `HbA1C` unit

All HbA1C values in this panel are in NGSP% (National Glycohemoglobin Standardization Program).  
Japan completed the transition from JDS to NGSP units in April 2013.  
Script 04 (`04_unit_title_audit.py`) confirms no JDS-labeled cells were found across any of the 11 releases.

### `LDL_cholesterol` and `HDL_cholesterol` (No.6–11)

NDB releases No.6–11 use full-width (double-byte) ASCII for cholesterol abbreviations
(e.g., "ＬＤＬ" instead of "LDL"). Script 05 applies NFKC Unicode normalization
(`unicodedata.normalize("NFKC", s)`) before label matching to handle this.

### Dental `metric_change` (No.8)

NDB No.8 (claims FY2021) switched the dental disease count metric from 傷病件数 (disease episode count)
to 算定回数 (procedure count). These two metrics are not directly comparable.
No.8 dental records are coded `metric_change` and excluded from main panel analyses.
