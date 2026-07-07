# Sonnet 4.6 Full Panel Extraction Prompt

## Master Prompt
Proceed to full 11-release panel extraction for Paper 1.

Use the initial NDB feasibility report as the basis. Do not start AI model fitting. Your goal is to create manuscript-ready evidence about NDB Open Data AI-readiness: full panels, coverage figures, missing/suppression profiles, feasibility summaries, and sensitivity tables.

Use these human decisions:
1. Exclude No.8 dental data from the main dental panel because the metric changes from disease counts to service/procedure counts. Record No.8 as metric_change and use it only in sensitivity or documentation.
2. Treat HbA1C as NGSP (%) only after checking title/unit rows across all releases. Report any release with ambiguous unit labeling.
3. Use visit-age aggregation for No.1 specific health checkup data to maintain consistency with later releases.
4. Exclude prefecture-unknown rows from the main prefecture-year panel, but retain them with missing_state = prefecture_unknown.
5. Use dental disease counts as the primary dental outcome. Treat dental procedure/service counts as a separate administrative utilization measure.
6. Keep questionnaire, medication, and rehabilitation indicators as secondary or supplementary candidates for now.
7. Do not impute suppressed cells in the main analysis.
8. Do not optimize or fit AI models in this phase.


## Required Outputs
1. `data/processed/ndb_prefecture_year_full_panel.csv`
2. `metadata/unit_title_audit.csv`
3. `tables/coverage_matrix.csv`
4. `tables/missing_suppression_profile.csv`
5. `tables/sensitivity_summary.csv`
6. `figures/temporal_coverage.png`
7. `figures/domain_missing_profile.png`
8. `reports/full_panel_handoff_to_manuscript.md`

## Main Decisions
- Exclude No.8 dental data from the main panel; record as `metric_change`.
- Verify HbA1C title/unit rows across all releases before treating values as NGSP (%).
- Use visit-age aggregation for No.1.
- Exclude prefecture-unknown rows from the main panel, but retain them with `missing_state = prefecture_unknown`.
- Use dental disease counts as the primary dental outcome.
- Keep questionnaire, medication, and rehabilitation indicators secondary for now.
- Do not fit AI models in this phase.

## Missing-State Vocabulary
- `observed`
- `suppressed`
- `unpublished`
- `metric_change`
- `prefecture_unknown`
- `parse_error`
- `not_applicable`

## Stop Condition
Stop and report back if extraction logic requires treating suppressed cells as zero, mixing disease counts with service/procedure counts, or choosing between conflicting HbA1C unit labels.
