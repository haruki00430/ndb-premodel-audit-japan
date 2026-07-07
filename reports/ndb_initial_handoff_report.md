# NDB Open Data Initial Handoff Report

**Project**: Paper 1 — "What Makes Administrative Healthcare Data AI-Ready?"
**Prepared by**: Sonnet 4.6 (NDB Initial Execution)
**Date**: 2026-07-06
**Status**: Phase 1 Complete — File Inventory, Feasibility Assessment, Prototype Extraction

---

## 1. Executive Summary

The NDB Open Data releases No.1–No.11 have been inventoried, candidate outcome items have been identified, and a prefecture-year feasibility assessment has been completed. A prototype long-format dataset has been extracted for 2 domains (diabetes/metabolic and dental/oral) across 3 time points.

**Key finding**: A reproducible prefecture-year panel CAN be built for diabetes/metabolic indicators using the specific health checkup examination data. Primary diabetes markers (HbA1C, fasting glucose) are available across all 11 releases at prefecture level, though with a documented naming inconsistency (HbA1C vs HbA1c) that must be handled. Dental indicators are partially feasible with important caveats.

---

## 2. Data Source Overview

### 2.1 File Inventory Summary

| Release | Files Found | Special Notes |
|---------|-------------|---------------|
| No.1 | 83 | 質問票なし; 特定健診「受診時年齢/年度末年齢」2フォルダ構造 |
| No.2 | 97 | 質問票が初めて追加（22項目、「都道府県別」表記なし） |
| No.3 | 138 | 質問票継続 |
| No.4 | 140 | 質問票継続 |
| No.5 | 149 | 質問票継続 |
| No.6 | 271 | **重大な構造変化**: 質問票に「都道府県別」「二次医療圏別」が分離 |
| No.7 | 304 | 同上 |
| No.8 | 311 | 同上 |
| No.9 | 402 | 同上 |
| No.10 | 609 | **重大な構造変化**: `01_公費レセプトを含まないデータ` サブフォルダが追加 |
| No.11 | 633 | 同上; 英訳版PDFが初めて追加 |

**Total files**: 3,137 Excel files across 11 releases

### 2.2 Release-Year Map

| Release | Claims FY | Checkup FY | Questionnaire | 2ndary Med. Area | Restructured |
|---------|-----------|------------|---------------|------------------|--------------|
| No.1 | FY2014 | FY2013 | No | No | No |
| No.2–5 | FY2015–18 | FY2014–17 | Yes (no pref label) | No | No |
| No.6–9 | FY2019–22 | FY2018–21 | Yes (pref labeled) | Yes | No |
| No.10–11 | FY2023–24 | FY2022–23 | Yes | Yes | Yes |

---

## 3. Candidate Outcome Item Feasibility

### 3.1 Grade A — Primary-Ready (18 items)

| Item | Family | n_years | Key Notes |
|------|--------|---------|-----------|
| HbA1C | diabetes_metabolic | 11/11 | **CRITICAL**: filename uses `HbA1C` (No.1–2, 11) vs `HbA1c` (No.3–10); case-insensitive matching required |
| fasting_glucose (空腹時血糖) | diabetes_metabolic | 11/11 | Most reliable diabetes marker in NDB |
| BMI | diabetes_metabolic | 11/11 | Available in all releases |
| waist_circumference (腹囲) | diabetes_metabolic | 11/11 | Central obesity marker |
| triglycerides (中性脂肪) | diabetes_metabolic | 11/11 | Metabolic syndrome |
| HDL_cholesterol | diabetes_metabolic | 10/11 | Missing in No.1 (check needed) |
| LDL_cholesterol | diabetes_metabolic | 10/11 | Missing in No.1 (check needed) |
| systolic_BP (収縮期血圧) | diabetes_metabolic | 11/11 | |
| diastolic_BP (拡張期血圧) | diabetes_metabolic | 11/11 | |
| mean_values_all_items | diabetes_metabolic | 11/11 | Composite file; contains HbA1C, glucose, BMI, etc. in one table |
| questionnaire_Q6_alcohol | diabetes_metabolic | 10/11 | Absent in No.1 |
| questionnaire_Q9_exercise | diabetes_metabolic | 10/11 | Absent in No.1 |
| questionnaire_Q11_eating_fast | diabetes_metabolic | 10/11 | Absent in No.1 |
| questionnaire_Q14_BMI_change | diabetes_metabolic | 10/11 | Absent in No.1 |
| dental_disease_counts_prefecture | dental_oral | 11/11 | **Format change**: 傷病件数→算定回数 in No.8; spacing change in No.7 |
| dental_act_count_prefecture | dental_oral | 10/11 | |
| prescription_drug_prefecture | medication | 11/11 | Prefecture-level prescription data |
| rehabilitation_acts | rehabilitation | 11/11 | H_リハビリテーション subfolder |

### 3.2 Grade B — Usable with Caveats (2 items)

| Item | n_years | Issue |
|------|---------|-------|
| urine_glucose (尿糖) | 9/11 | Missing in 2 releases (check which) |
| questionnaire_Q1_smoking | 10/11 | Absent in No.1; questionnaire not published |

### 3.3 Grade C — Documentation Only (5 items)

| Item | n_years | Issue |
|------|---------|-------|
| random_glucose (随時血糖) | 6/11 | Added later in No.6 onwards |
| eGFR | 6/11 | Added later; No.10–11 only + some earlier |
| serum_creatinine (血清クレアチニン) | 6/11 | Same as eGFR |
| dental_disease_sex_age | 11/11 | Sex/age data is national, not prefecture-level |
| dental_act_patients_prefecture | 3/11 | Very limited coverage |

---

## 4. Prototype Dataset Summary

**File**: `data/processed/ndb_prefecture_year_prototype.csv`

| Metric | Value |
|--------|-------|
| Total records | 30,099 |
| Years covered | 2013, 2014, 2018, 2019, 2023, 2024 |
| Prefectures | 47 (+ 1 "prefecture_unknown" entry) |
| Domains | diabetes_metabolic (11,440), dental_oral (18,659) |
| Observed values | 23,680 (78.7%) |
| Suppressed values | 6,419 (21.3%) |
| Missing_unknown | 0 |
| Parse_errors | 0 |

### 4.1 Missing State Breakdown

- **observed**: Valid numeric value extracted
- **suppressed**: Cell value is `-` or `－` (count < 10 threshold per NDB suppression rules)
- **missing_unknown**: None in this prototype
- **parse_error**: None in this prototype

### 4.2 Suppression Pattern

Suppression (21.3%) is concentrated in the dental disease domain (dental_oral). The diabetes/metabolic indicators (mean values from health checkup) have **0% suppression** because they report continuous means, not counts. This is a major data quality advantage for the diabetes/metabolic domain.

---

## 5. Structural Changes Documented

### Critical Format Changes (must be handled in production pipeline)

1. **HbA1C naming inconsistency**
   - No.1–2, No.11: `HbA1C` (uppercase C)
   - No.3–10: `HbA1c` (lowercase c)
   - **Action required**: Case-insensitive file matching in extraction script

2. **Questionnaire file structure change (No.2–5 vs No.6–9)**
   - No.2–5: Single xlsx per question, no "都道府県別" in filename
   - No.6–9: Separate files with "都道府県別性年齢階級別分布" and "二次医療圏別..." in filename
   - **Action required**: Two parsing branches in questionnaire extractor

3. **Public fee exclusion restructuring (No.10–11)**
   - No.10–11 added `01_公費レセプトを含まないデータ` intermediate folder
   - **Action required**: Path resolution must handle this extra subfolder

4. **Dental disease metric change (No.8)**
   - No.1–7, 9: `傷病件数.xlsx`
   - No.8: `算定回数.xlsx` (different metric)
   - **Action required**: No.8 dental disease may not be comparable with other releases

5. **Dental disease filename spacing (No.7 onwards)**
   - No.1–6: `都道府県別　傷病件数.xlsx` (full-width space before 傷病)
   - No.7+: `都道府県別傷病件数.xlsx` (no space)
   - **Action required**: Pattern matching must not rely on exact spacing

---

## 6. Outputs Ready for Paper 1 Manuscript

### Ready for Results Section
- **Table 1**: File inventory summary (metadata/ndb_file_inventory.csv)
- **Table 2**: Release-year mapping (metadata/ndb_release_year_map.csv)
- **Table 3**: Candidate outcome feasibility table (tables/prefecture_year_feasibility.csv)
- **Figure 1**: Temporal coverage heatmap (to be generated from feasibility table)
- **Appendix**: Full candidate outcome items table (tables/candidate_outcome_items.csv)

### Not Ready / Requires Confirmation
- Individual prefecture-year mean values (prototype only; full extraction pending confirmation of suppression handling approach)
- Dental disease trends (format change in No.8 requires decision on comparability)
- Questionnaire binary indicators (need decision on reference period definition)

---

## 7. Recommended Next Steps

1. **Confirm suppression handling policy** — Should No.8 dental disease (算定回数 vs 傷病件数) be treated as comparable or flagged as format_change?
2. **Confirm questionnaire reference years** — No.1 has no questionnaire; does the analysis start from No.2 (FY2014)?
3. **Validate prefecture-year panel completeness** — Run full extraction across all 11 releases for the 5 primary Grade A items
4. **Build temporal coverage figure** — Visualize which items × years × prefectures have observed vs suppressed data
5. **Decide on age-group aggregation** — The prototype has sex × age_group; does the primary analysis use totals or age-standardized values?

---

## 8. Non-Negotiable Rules Compliance

- [x] Raw files were not overwritten (read-only access only)
- [x] No data was invented
- [x] Suppressed cells were coded as `suppressed`, not merged with `missing_unknown`
- [x] No AI model fitting was performed
- [x] Format changes were documented separately, not silently resolved
- [x] Province-year panel feasibility was assessed before any analysis

---

*This report was generated by Sonnet 4.6 as the NDB Initial Execution agent. All outputs are in `projects/NDB-20260706/`.*
