"""
Coverage matrix, missing/suppression profiles, and sensitivity tables.
Reads: data/processed/ndb_prefecture_year_full_panel.csv
Outputs:
  tables/coverage_matrix.csv
  tables/missing_suppression_profile.csv
  tables/sensitivity_summary.csv
"""

import sys
import logging
from pathlib import Path
from collections import Counter

import pandas as pd

SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
DATA_DIR = PROJECT_DIR / "data" / "processed"
TABLES_DIR = PROJECT_DIR / "tables"
TABLES_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

MISSING_STATES = [
    "observed", "suppressed", "unpublished", "metric_change",
    "prefecture_unknown", "parse_error", "not_applicable", "missing_unknown",
]


def load_panel():
    path = DATA_DIR / "ndb_prefecture_year_full_panel.csv"
    logger.info(f"Loading: {path}")
    df = pd.read_csv(path, encoding="utf-8-sig", dtype=str)
    logger.info(f"  Loaded {len(df)} records")
    return df


def build_coverage_matrix(df: pd.DataFrame):
    """
    Coverage matrix: indicator × fiscal_year × prefecture.
    Cell value = missing_state (or 'observed' / 'suppressed' / etc.)
    Aggregated output: indicator × fiscal_year, with counts per state.
    """
    # Focus on primary panel (exclude prefecture_unknown from main)
    main = df[~df["missing_state"].isin(["prefecture_unknown"])].copy()

    # Metabolic: aggregate across sex/age to get unique prefecture × indicator × year
    metabolic = main[main["domain"] == "diabetes_metabolic"].copy()
    dental = main[main["domain"] == "dental_oral"].copy()

    rows = []

    # Metabolic coverage by indicator × release
    for (indicator, release_no), grp in metabolic.groupby(
        ["indicator_name", "release_no"]
    ):
        fy = grp["fiscal_year"].iloc[0]
        state_counts = grp["missing_state"].value_counts().to_dict()
        # Count distinct prefectures with observed values
        obs_prefs = grp[grp["missing_state"] == "observed"]["prefecture_code"].nunique()
        sup_prefs = grp[grp["missing_state"] == "suppressed"]["prefecture_code"].nunique()
        rows.append({
            "domain": "diabetes_metabolic",
            "indicator_name": indicator,
            "release_no": release_no,
            "fiscal_year": fy,
            "data_year_type": grp["data_year_type"].iloc[0],
            "n_prefecture_observed": obs_prefs,
            "n_prefecture_suppressed": sup_prefs,
            "n_prefecture_total": 47,
            "coverage_pct": round(obs_prefs / 47 * 100, 1),
            "n_records_total": len(grp),
            "n_records_observed": state_counts.get("observed", 0),
            "n_records_suppressed": state_counts.get("suppressed", 0),
            "n_records_other": sum(v for k, v in state_counts.items()
                                   if k not in ("observed", "suppressed")),
        })

    # Dental coverage by release (aggregated, not by individual disease code)
    # Use disease group level: indicator_name contains disease group
    if len(dental) > 0:
        for release_no, grp in dental.groupby("release_no"):
            fy = grp["fiscal_year"].iloc[0]
            main_state = grp["missing_state"].mode().iloc[0] if len(grp) > 0 else "unknown"
            state_counts = grp["missing_state"].value_counts().to_dict()
            obs_prefs = grp[grp["missing_state"] == "observed"]["prefecture_code"].nunique()
            rows.append({
                "domain": "dental_oral",
                "indicator_name": "dental_disease_counts_all_groups",
                "release_no": release_no,
                "fiscal_year": fy,
                "data_year_type": grp["data_year_type"].iloc[0],
                "n_prefecture_observed": obs_prefs,
                "n_prefecture_suppressed": grp[grp["missing_state"] == "suppressed"]["prefecture_code"].nunique(),
                "n_prefecture_total": 47,
                "coverage_pct": round(obs_prefs / 47 * 100, 1) if main_state != "metric_change" else 0,
                "n_records_total": len(grp),
                "n_records_observed": state_counts.get("observed", 0),
                "n_records_suppressed": state_counts.get("suppressed", 0),
                "n_records_other": sum(v for k, v in state_counts.items()
                                       if k not in ("observed", "suppressed")),
            })

    cov_df = pd.DataFrame(rows)
    out_path = TABLES_DIR / "coverage_matrix.csv"
    cov_df.to_csv(out_path, index=False, encoding="utf-8-sig")
    logger.info(f"Coverage matrix: {out_path} ({len(cov_df)} rows)")
    return cov_df


def build_missing_suppression_profile(df: pd.DataFrame):
    """
    Missing/suppression profile:
    - By domain, indicator_name, fiscal_year: count of each missing_state
    """
    rows = []
    for (domain, indicator, fy), grp in df.groupby(
        ["domain", "indicator_name", "fiscal_year"]
    ):
        state_counts = grp["missing_state"].value_counts().to_dict()
        total = len(grp)
        row = {
            "domain": domain,
            "indicator_name": indicator,
            "fiscal_year": fy,
            "data_year_type": grp["data_year_type"].iloc[0],
            "n_total": total,
        }
        for state in MISSING_STATES:
            row[f"n_{state}"] = state_counts.get(state, 0)
            row[f"pct_{state}"] = round(
                state_counts.get(state, 0) / total * 100, 1
            ) if total > 0 else 0.0
        rows.append(row)

    prof_df = pd.DataFrame(rows)
    out_path = TABLES_DIR / "missing_suppression_profile.csv"
    prof_df.to_csv(out_path, index=False, encoding="utf-8-sig")
    logger.info(f"Missing/suppression profile: {out_path} ({len(prof_df)} rows)")
    return prof_df


def build_sensitivity_summary(df: pd.DataFrame, cov_df: pd.DataFrame):
    """
    Sensitivity table: 3 scenarios
      Scenario A: Main panel (No.8 excluded via metric_change, prefecture_unknown excluded)
      Scenario B: Include No.8 as if metric_change were comparable (sensitivity check)
      Scenario C: Exclude prefectures with any suppressed cell across all years
    """
    rows = []

    # Metabolic indicators
    metabolic_main = df[
        (df["domain"] == "diabetes_metabolic") &
        (~df["missing_state"].isin(["prefecture_unknown", "missing_unknown"]))
    ].copy()

    metabolic_indicators = metabolic_main["indicator_name"].unique()

    for indicator in sorted(metabolic_indicators):
        ind_df = metabolic_main[metabolic_main["indicator_name"] == indicator]

        # Scenario A: Main panel
        n_releases = ind_df["release_no"].nunique()
        n_obs_cells = len(ind_df[ind_df["missing_state"] == "observed"])
        n_sup_cells = len(ind_df[ind_df["missing_state"] == "suppressed"])
        n_total = len(ind_df)
        obs_pct = round(n_obs_cells / n_total * 100, 1) if n_total > 0 else 0

        # Scenario C: prefectures with zero suppression across all years
        pref_sup = ind_df.groupby("prefecture_code").apply(
            lambda g: (g["missing_state"] == "suppressed").any()
        )
        n_clean_prefs = int((~pref_sup).sum())

        rows.append({
            "scenario": "A_main_panel",
            "domain": "diabetes_metabolic",
            "indicator_name": indicator,
            "n_releases": n_releases,
            "n_records_total": n_total,
            "n_observed": n_obs_cells,
            "n_suppressed": n_sup_cells,
            "obs_pct": obs_pct,
            "n_prefectures_zero_suppression": n_clean_prefs,
            "notes": "Main panel: No.8 dental excluded; prefecture_unknown excluded",
        })

    # Dental: Scenario A (No.8 = metric_change, excluded)
    dental_main = df[
        (df["domain"] == "dental_oral") &
        (df["missing_state"] != "metric_change") &
        (df["missing_state"] != "prefecture_unknown")
    ].copy()
    dental_releases = dental_main[
        dental_main["missing_state"] == "observed"
    ]["release_no"].nunique()
    n_dental_obs = (dental_main["missing_state"] == "observed").sum()
    n_dental_sup = (dental_main["missing_state"] == "suppressed").sum()
    n_dental_total = len(dental_main)

    rows.append({
        "scenario": "A_main_panel",
        "domain": "dental_oral",
        "indicator_name": "dental_disease_counts",
        "n_releases": dental_releases,
        "n_records_total": n_dental_total,
        "n_observed": int(n_dental_obs),
        "n_suppressed": int(n_dental_sup),
        "obs_pct": round(n_dental_obs / n_dental_total * 100, 1) if n_dental_total > 0 else 0,
        "n_prefectures_zero_suppression": "N/A",
        "notes": "No.8 excluded (metric_change: 算定回数 not 傷病件数)",
    })

    # Scenario B: Dental with No.8 included (as metric_change, treating it as sensitivity)
    dental_b = df[
        (df["domain"] == "dental_oral") &
        (df["missing_state"] != "prefecture_unknown")
    ].copy()
    n_dental_b_mc = (dental_b["missing_state"] == "metric_change").sum()
    rows.append({
        "scenario": "B_include_No8_metric_change",
        "domain": "dental_oral",
        "indicator_name": "dental_disease_counts",
        "n_releases": 11,
        "n_records_total": len(dental_b),
        "n_observed": int((dental_b["missing_state"] == "observed").sum()),
        "n_suppressed": int((dental_b["missing_state"] == "suppressed").sum()),
        "obs_pct": "N/A",
        "n_prefectures_zero_suppression": "N/A",
        "notes": f"No.8 included as metric_change ({n_dental_b_mc} records); not comparable to other releases",
    })

    # Scenario C: HbA1C with prefecture_unknown retained
    hba1c_c = df[
        (df["domain"] == "diabetes_metabolic") &
        (df["indicator_name"] == "HbA1C")
    ].copy()
    n_pref_unk = (hba1c_c["missing_state"] == "prefecture_unknown").sum()
    rows.append({
        "scenario": "C_retain_prefecture_unknown",
        "domain": "diabetes_metabolic",
        "indicator_name": "HbA1C",
        "n_releases": hba1c_c["release_no"].nunique(),
        "n_records_total": len(hba1c_c),
        "n_observed": int((hba1c_c["missing_state"] == "observed").sum()),
        "n_suppressed": int((hba1c_c["missing_state"] == "suppressed").sum()),
        "obs_pct": round(
            (hba1c_c["missing_state"] == "observed").sum() / len(hba1c_c) * 100, 1
        ) if len(hba1c_c) > 0 else 0,
        "n_prefectures_zero_suppression": "N/A",
        "notes": f"prefecture_unknown retained ({n_pref_unk} records added back)",
    })

    sens_df = pd.DataFrame(rows)
    out_path = TABLES_DIR / "sensitivity_summary.csv"
    sens_df.to_csv(out_path, index=False, encoding="utf-8-sig")
    logger.info(f"Sensitivity summary: {out_path} ({len(sens_df)} rows)")
    return sens_df


def main():
    df = load_panel()

    logger.info("\n=== Building Coverage Matrix ===")
    cov_df = build_coverage_matrix(df)

    logger.info("\n=== Building Missing/Suppression Profile ===")
    prof_df = build_missing_suppression_profile(df)

    logger.info("\n=== Building Sensitivity Summary ===")
    sens_df = build_sensitivity_summary(df, cov_df)

    # Quick summary report
    logger.info("\n=== Summary ===")
    total = len(df)
    state_counts = df["missing_state"].value_counts()
    logger.info(f"Total records: {total}")
    for state, cnt in state_counts.items():
        logger.info(f"  {state}: {cnt} ({cnt/total*100:.1f}%)")

    # Coverage for primary metabolic indicators (total sex/age)
    total_only = df[
        (df["domain"] == "diabetes_metabolic") &
        (df["age_group"] == "total") &
        (df["sex"].isin(["male", "female"]))
    ]
    logger.info(f"\nMetabolic total-level records: {len(total_only)}")
    for ind, grp in total_only.groupby("indicator_name"):
        obs = (grp["missing_state"] == "observed").sum()
        tot = len(grp)
        logger.info(f"  {ind}: {obs}/{tot} observed ({obs/tot*100:.0f}%)")


if __name__ == "__main__":
    main()
