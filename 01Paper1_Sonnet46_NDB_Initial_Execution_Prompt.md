# Sonnet 4.6 NDB Open Data Initial Execution Prompt

## Master Prompt
You are the Python implementation lead for Paper 1, "What Makes Administrative Healthcare Data AI-Ready?"

Use NDB Open Data as the primary data source. Your first job is not to build a prediction model. Your first job is to determine whether the NDB Open Data releases can support a reproducible prefecture-year panel for diabetes/metabolic indicators and dental/oral-care indicators.

Build a transparent file inventory for the 1st through 11th NDB Open Data releases. Identify candidate diabetes/metabolic and dental/oral-care items. Test whether each candidate item can be extracted consistently by year and prefecture. Record sex and age-group availability when present. Treat missing values, suppressed cells, unpublished cells, format changes, and structurally unavailable data as different states.

Do not overwrite raw files. Do not invent data. Do not impute suppressed cells unless explicitly asked in a sensitivity analysis. Do not optimize AI model performance. Produce data dictionaries, feasibility tables, reliability indicators, figures, and a handoff report that states which outputs can be used in the manuscript Results.


## First Deliverables
1. `metadata/ndb_file_inventory.csv`
2. `metadata/ndb_release_year_map.csv`
3. `tables/candidate_outcome_items.csv`
4. `tables/prefecture_year_feasibility.csv`
5. `data/processed/ndb_prefecture_year_prototype.csv`
6. `reports/ndb_initial_handoff_report.md`
7. `reports/assumptions_to_confirm.md`

## Primary Candidate Families
- Diabetes/metabolic indicators.
- Dental/oral-care indicators.

## Secondary Candidate Families
- Medication prescribing indicators.
- Rehabilitation-related service indicators.

## Feasibility Grades
- A: primary-ready.
- B: usable with caveats.
- C: documentation-only.
- D: not usable.

## Non-negotiable Rules
- Do not overwrite raw files.
- Do not invent data.
- Do not collapse suppressed, unpublished, blank, not applicable, and parse-error states into one generic missing value.
- Do not start with AI model fitting.
- Do not optimize model performance.
- First prove whether a reproducible prefecture-year panel can be built.
