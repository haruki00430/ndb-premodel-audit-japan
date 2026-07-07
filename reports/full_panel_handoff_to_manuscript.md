# Full Panel Extraction Handoff: NDB Open Data AI-Readiness

**Paper 1**: "What Makes Administrative Healthcare Data AI-Ready?"  
**Phase**: Full 11-Release Panel Extraction → Manuscript Stage  
**作成日**: 2026年7月6日  
**作成者**: Claude Sonnet 4.6 (scripts 04–07)  
**前段階**: Initial feasibility (scripts 01–03) — 3,137 files inventoried, 25 candidate items assessed, prototype of 30,099 records

---

## 1. What this phase produced

This phase executed the full 11-release extraction of Grade A primary indicators and produced manuscript-ready evidence tables and figures for Paper 1.  No AI model was fitted in this phase.

| Output | Location | Rows/Size |
|--------|----------|-----------|
| Full panel CSV | `data/processed/ndb_prefecture_year_full_panel.csv` | 146,376 records |
| Unit/title audit | `metadata/unit_title_audit.csv` | 11 rows (1 per release) |
| Coverage matrix | `tables/coverage_matrix.csv` | 110 rows |
| Missing/suppression profile | `tables/missing_suppression_profile.csv` | 1,611 rows |
| Sensitivity summary | `tables/sensitivity_summary.csv` | 12 rows |
| Temporal coverage figure | `figures/temporal_coverage.png` | heatmap |
| Domain missing profile figure | `figures/domain_missing_profile.png` | bar chart |

---

## 2. Panel structure

The full panel covers two primary domains:

### 2a. Diabetes/Metabolic Domain (Specific Health Checkup data)

**Source**: 各項目の平均値 都道府県別性年齢階級別分布 (per-item mean values, prefecture × sex × age)  
**Year type**: specific_health_checkup  
**Fiscal years covered**: FY2013–FY2023 (11 releases)

| Indicator | Releases | Prefecture coverage | Suppressed |
|-----------|----------|---------------------|-----------|
| HbA1C | 11/11 | 100% (47/47) all years | 0% |
| Fasting glucose | 11/11 | 100% | 0% |
| BMI | 11/11 | 100% | 0% |
| Waist circumference | 11/11 | 100% | 0% |
| Systolic BP | 11/11 | 100% | 0% |
| Diastolic BP | 11/11 | 100% | 0% |
| Triglycerides | 11/11 | 100% | 0% |
| LDL cholesterol | 11/11 | 100% | 0% |
| HDL cholesterol | 11/11 | 100% | 0% |

**Key finding**: The diabetes/metabolic mean-value panel has 100% prefecture coverage and 0% suppression across all 11 releases and all 9 primary indicators. The checkup mean-value files are the most AI-ready component of NDB Open Data.

### 2b. Dental/Oral Domain (Claims data)

**Source**: 都道府県別 傷病件数 (prefecture-level disease counts)  
**Year type**: claims  
**Fiscal years covered**: FY2014–FY2020, FY2022–FY2024 (10 releases; No.8/FY2021 = metric_change)

| Release | Claims FY | Prefecture coverage | Observed records | Suppressed records |
|---------|-----------|---------------------|------------------|--------------------|
| No.1 | FY2014 | 100% | 3,744 | 3,306 (46.9%) |
| No.2 | FY2015 | 100% | 3,867 | 3,136 (44.8%) |
| No.3 | FY2016 | 100% | 3,996 | 3,101 (43.7%) |
| No.4 | FY2017 | 100% | 3,853 | 3,291 (46.1%) |
| No.5 | FY2018 | 100% | 4,187 | 2,863 (40.6%) |
| No.6 | FY2019 | 100% | 4,179 | 2,965 (41.5%) |
| No.7 | FY2020 | 100% | 4,097 | 3,047 (42.6%) |
| **No.8** | **FY2021** | **metric_change** | **0** | **0** |
| No.9 | FY2022 | 100% | 5,874 | 1,364 (18.8%) |
| No.10 | FY2023 | 100% | 5,789 | 1,402 (19.5%) |
| No.11 | FY2024 | 100% | 5,699 | 1,257 (18.1%) |

**Key finding**: Prefecture coverage is 100% in all releases where disease counts were published. Cell-level suppression (counts < 10 per ICD code × prefecture) was high in FY2014–FY2020 (~41–47%) and decreased to ~19% in FY2022–FY2024. Suppression concentrates in rare dental ICD codes, not in major disease groups (caries, periodontal disease).

---

## 3. Human decisions applied (and their effects)

| Decision | Applied | Effect on panel |
|----------|---------|----------------|
| **#1** No.8 dental excluded (metric_change) | ✅ | 47 records coded metric_change; not in main dental panel |
| **#2** HbA1C = NGSP (%) — verify first | ✅ (see Unit Audit) | No JDS found; all releases treated as NGSP |
| **#3** No.1 visit-age aggregation | ✅ | 受診時年齢 subfolder selected for No.1 |
| **#4** prefecture_unknown retained, excluded from main | ✅ | 864 records coded prefecture_unknown |
| **#5** dental disease counts = primary | ✅ | 傷病件数 selected; No.8 算定回数 = metric_change |
| **#6** questionnaire/medication/rehab = secondary | ✅ | Not extracted in this phase |
| **#7** No imputation | ✅ | suppressed cells left as NaN, missing_state="suppressed" |
| **#8** No AI model fitting | ✅ | Panel + coverage only; no model code |

---

## 4. Unit/Title Audit: HbA1C (Stop Condition Check)

**Question**: Is HbA1C consistently labeled NGSP across all 11 releases?  
**Finding**: No JDS label found in any release. **Stop Condition NOT triggered.**

| Release group | Label in source file | Explicit NGSP | Ambiguous | Notes |
|--------------|---------------------|---------------|-----------|-------|
| No.1–2 | `HbA1C(NGSP)[%]` | Yes | No | Uppercase C |
| No.3–5 | `HbA1c(NGSP)[%]` | Yes | No | Lowercase c |
| No.6–11 | `HbA1C` | No | Yes (implicit) | Label dropped after FY2018 |

**Interpretation**: No.6–11 drop the explicit "(NGSP)[%]" label. However, Japan's mandatory NGSP transition was completed in April 2013. Since all NDB releases are FY2013 or later, all values are NGSP by policy. No JDS value was found in any file. The manuscript should note that explicit NGSP labeling was dropped in No.6 and document this as an undocumented format change.

**Technical note**: HbA1C file labels also differ by case (No.1–2, 6–11: `HbA1C`; No.3–5: `HbA1c`). Case-insensitive matching was applied to ensure consistent extraction across all releases.

---

## 5. Structural changes documented

Five structural changes were detected across the 11-release series:

| # | Change | Releases affected | Handling |
|---|--------|------------------|----------|
| 1 | HbA1C filename: `HbA1C` vs `HbA1c` (uppercase/lowercase C) | No.1–2 vs No.3–10 vs No.11 | Case-insensitive "HbA1" pattern |
| 2 | No.1 has two age aggregation options (visit-age / year-end age) | No.1 only | visit-age selected (Decision #3) |
| 3 | Dental metric change: 傷病件数 → 算定回数 → 傷病件数 | No.8 only | metric_change flag |
| 4 | LDL/HDL label: full with コレステロール (No.1–5) vs abbreviated (No.6–11) | No.6–11 | NFKC normalization + reverse pattern match |
| 5 | Folder restructuring: 01_公費レセプトを含まないデータ/ introduced | No.10–11 | Path priority logic updated |

---

## 6. Missing state distribution (full panel)

| missing_state | Records | % |
|---------------|---------|---|
| **observed** | **119,733** | **81.8%** |
| suppressed | 25,732 | 17.6% |
| prefecture_unknown | 864 | 0.6% |
| metric_change | 47 | 0.03% |
| **Total** | **146,376** | **100%** |

**Note**: Suppression is entirely in the dental domain (disease code × prefecture cells with count < 10). The diabetes/metabolic mean-value domain has zero suppressed cells.

---

## 7. Sensitivity analyses

Three scenarios were evaluated:

**Scenario A (Main panel)**: No.8 excluded (metric_change), prefecture_unknown excluded.
- Metabolic: 9 indicators × 11 releases × 47 prefectures × 2 sexes × 8 age groups = 100% observed (no suppression)
- Dental: 10 releases × 47 prefectures × ~150 disease codes = 63.8% observed, 36.2% suppressed

**Scenario B**: No.8 included with metric_change flag (for documentation).
- Adds 47 metric_change records (one per prefecture). No observed values from No.8.

**Scenario C**: HbA1C with prefecture_unknown retained.
- Adds 96 prefecture_unknown records. Overall observed rate 98.9% (vs 99% in Scenario A).

---

## 8. What goes into the Results section

The following findings are ready for the Paper 1 Results section:

**Finding R1** (Table 1 / Table 2 material):
NDB Open Data supports a reproducible 47-prefecture × 11-release panel for all 9 primary diabetes/metabolic indicators (HbA1C, fasting glucose, BMI, waist circumference, systolic BP, diastolic BP, triglycerides, LDL cholesterol, HDL cholesterol). Prefecture coverage is 100% in all releases. Observed cell rate is 100% (no suppression in mean-value files).

**Finding R2** (Table 2 / Figure 1 material):
The dental disease-count panel covers 10 of 11 releases (No.8/FY2021 excluded due to metric change). Prefecture coverage is 100% per release. Cell-level suppression decreased from ~47% (FY2014–2017) to ~19% (FY2022–2024), indicating improved reporting completeness over time.

**Finding R3** (Table 3 material):
HbA1C explicit NGSP labeling was dropped after No.5/FY2017 without documentation. This represents an undocumented format change that would cause silent failure in automated pipelines relying on label-based unit detection.

**Finding R4** (Table 4 material):
No.8/FY2021 dental data used a different metric (算定回数 = procedure count) instead of the standard 傷病件数 (disease count). This one-release metric change breaks cross-year comparability and must be documented as a data quality event for any AI readiness framework.

**Finding R5** (Table 4 / Sensitivity table material):
Five undocumented structural changes were detected across the 11-release series. None caused data loss for primary indicators, but all required bespoke extraction logic that would not be captured by standard data loading routines.

---

## 9. What remains before final manuscript

| Task | Status | Notes |
|------|--------|-------|
| Full panel extracted | ✅ Done | 146,376 records, all formats resolved |
| Unit audit | ✅ Done | No JDS conflict; NGSP implicit in No.6–11 |
| Coverage figures | ✅ Done | 2 publication-quality PNGs at 300 dpi |
| Sensitivity table | ✅ Done | 3 scenarios documented |
| Questionnaire binary indicators | ⏳ Pending | Q1–Q22, secondary/supplementary |
| Medication (prescription drug) indicators | ⏳ Pending | Secondary for this phase |
| Rehabilitation indicators | ⏳ Pending | Secondary for this phase |
| Manuscript Table 1–4 drafting | ⏳ Next step | Based on findings R1–R5 above |
| Paper 1 Results section writing | ⏳ Next step | Use findings R1–R5; do not interpret as model performance |

---

## 10. File provenance

All output files were generated from:
- Raw data: `02_Data/raw/NDB_OpenData/No.{1-11}/` (read-only, not modified)
- Scripts: `projects/ndb-premodel-audit-japan/scripts/04_unit_title_audit.py` through `07_figures.py`
- No data was invented. No suppressed cells were imputed.
- No AI model was fitted.

```
scripts/04_unit_title_audit.py     → metadata/unit_title_audit.csv
scripts/05_full_panel_extraction.py → data/processed/ndb_prefecture_year_full_panel.csv
scripts/06_coverage_profiles.py    → tables/coverage_matrix.csv
                                   → tables/missing_suppression_profile.csv
                                   → tables/sensitivity_summary.csv
scripts/07_figures.py              → figures/temporal_coverage.png
                                   → figures/domain_missing_profile.png
```

---

## 11. Reproduction

```bash
cd research_workspace/projects/NDB_Research_Hub
python projects/ndb-premodel-audit-japan/scripts/04_unit_title_audit.py
python projects/ndb-premodel-audit-japan/scripts/05_full_panel_extraction.py
python projects/ndb-premodel-audit-japan/scripts/06_coverage_profiles.py
python projects/ndb-premodel-audit-japan/scripts/07_figures.py
```

Expected output: 146,376 records total; 119,733 observed (81.8%); 25,732 suppressed (17.6%).

---

*Required report statement (per Full Panel Extraction Prompt):*  
NDB Open Data supports a reproducible prefecture-year panel for the primary diabetes/metabolic indicators across all 11 releases (FY2013–FY2023), with 100% prefecture coverage and 0% suppression in mean-value files. For dental disease counts, coverage is 100% across 10 of 11 releases (FY2014–FY2024, excluding No.8/FY2021 which used a different metric). Suppressed cells occur at the disease code × prefecture level in the dental domain, with rates declining from ~47% (FY2014) to ~19% (FY2024). Observed values, suppressed cells, metric-change records, and prefecture-unknown rows are kept separate throughout. These findings describe data structure and coverage; they do not represent model performance.
