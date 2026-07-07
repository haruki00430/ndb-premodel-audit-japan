#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Publication-Quality Figure Generation for Paper 1
論文掲載品質図の生成スクリプト（300 dpi PNG × 2 枚）

Outputs / 出力:
  figures/temporal_coverage.png      — 指標 × 年度 カバレッジヒートマップ (Figure 1)
  figures/domain_missing_profile.png — ドメイン別欠損状態積み上げ棒グラフ (Figure 2)

What this script does / このスクリプトの目的:
  Script 06 が生成したカバレッジマトリクスと欠損プロファイルを読み込み、
  論文に掲載するための図を 300 dpi PNG で生成する。

Figure descriptions / 図の説明:
  Figure 1 (temporal_coverage.png):
    横軸 = 年度（FY2013-2024）、縦軸 = 指標名
    セル値 = 47 都道府県のうち観測値が取れた割合（%）
    カラースケール: 赤（0%）→ オレンジ（50%）→ 緑（100%）、灰色 = NaN
  Figure 2 (domain_missing_profile.png):
    横軸 = 指標名、縦軸 = レコード数
    欠損状態ごとに色分けした積み上げ棒グラフ（左: 糖尿病/メタボ、右: 歯科）

Security rules / セキュリティルール:
  - Reads derived tables only / 派生テーブルのみ読み込む
  - Never writes to raw/ / raw/ には書き込まない
"""

import sys
import logging
from pathlib import Path

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.colors import ListedColormap

SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
DATA_DIR = PROJECT_DIR / "data" / "processed"
TABLES_DIR = PROJECT_DIR / "tables"
FIGURES_DIR = PROJECT_DIR / "figures"
FIGURES_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# Set Japanese font
try:
    import sys
    sys.path.insert(0, str(PROJECT_DIR.parents[1] / "src"))
    from ndb_library.viz import set_japanese_font
    set_japanese_font()
    logger.info("Japanese font set via ndb_library")
except Exception:
    try:
        import matplotlib.font_manager as fm
        # Try Windows Japanese fonts
        for font_name in ["Meiryo", "MS Gothic", "Yu Gothic", "IPAexGothic"]:
            fonts = [f for f in fm.findSystemFonts() if font_name in f]
            if fonts:
                plt.rcParams["font.family"] = font_name
                logger.info(f"Font set: {font_name}")
                break
    except Exception:
        logger.warning("Japanese font not available; labels may show boxes")


def figure_temporal_coverage():
    """
    指標 × 年度 × 都道府県カバレッジのヒートマップを生成する（Figure 1）。
    Generate the indicator × fiscal-year prefecture coverage heatmap (Figure 1).

    Script 06 が出力した coverage_matrix.csv を読み込み、
    各セルに都道府県カバレッジ率（%）を色づけしたヒートマップを描画する。
    赤（0%）→ 橙（50%）→ 緑（100%）のカラースケールを使用。
    糖尿病/メタボ指標と歯科指標を破線で区切って表示する。

    Input:  tables/coverage_matrix.csv
    Output: figures/temporal_coverage.png (300 dpi)
    """
    cov_path = TABLES_DIR / "coverage_matrix.csv"
    if not cov_path.exists():
        logger.error(f"Coverage matrix not found: {cov_path}")
        return

    cov = pd.read_csv(cov_path, encoding="utf-8-sig")
    cov["fiscal_year"] = pd.to_numeric(cov["fiscal_year"], errors="coerce")
    cov["coverage_pct"] = pd.to_numeric(cov["coverage_pct"], errors="coerce").fillna(0)

    # Separate domains
    metabolic = cov[cov["domain"] == "diabetes_metabolic"].copy()
    dental = cov[cov["domain"] == "dental_oral"].copy()

    # Sort indicators
    INDICATOR_ORDER = [
        "HbA1C", "fasting_glucose", "BMI", "waist_circumference",
        "systolic_BP", "diastolic_BP", "triglycerides",
        "LDL_cholesterol", "HDL_cholesterol",
    ]

    INDICATOR_LABELS = {
        "HbA1C": "HbA1C (NGSP%)",
        "fasting_glucose": "Fasting glucose",
        "BMI": "BMI",
        "waist_circumference": "Waist circumf.",
        "systolic_BP": "Systolic BP",
        "diastolic_BP": "Diastolic BP",
        "triglycerides": "Triglycerides",
        "LDL_cholesterol": "LDL cholesterol",
        "HDL_cholesterol": "HDL cholesterol",
        "dental_disease_counts_all_groups": "Dental disease\ncounts",
    }

    # Build pivot: indicator (rows) × fiscal_year (cols)
    # Aggregate across sex/age: take mean coverage_pct for each indicator×year
    metabolic_piv = metabolic.groupby(["indicator_name", "fiscal_year"])[
        "coverage_pct"
    ].first().unstack(level="fiscal_year")

    # Only include known indicators
    metabolic_piv = metabolic_piv.reindex(
        [i for i in INDICATOR_ORDER if i in metabolic_piv.index]
    )

    dental_piv = dental.groupby(["indicator_name", "fiscal_year"])[
        "coverage_pct"
    ].first().unstack(level="fiscal_year")

    # Combine
    all_rows = []
    for ind in metabolic_piv.index:
        all_rows.append((ind, metabolic_piv.loc[ind]))
    for ind in dental_piv.index:
        all_rows.append((ind, dental_piv.loc[ind]))

    if not all_rows:
        logger.error("No data for temporal coverage figure")
        return

    # All fiscal years from panel
    all_fy = sorted(set(cov["fiscal_year"].dropna().astype(int)))

    # Build matrix
    matrix = []
    ylabels = []
    for ind, series in all_rows:
        row = [series.get(fy, np.nan) for fy in all_fy]
        matrix.append(row)
        ylabels.append(INDICATOR_LABELS.get(ind, ind))

    matrix = np.array(matrix, dtype=float)

    fig, ax = plt.subplots(figsize=(13, len(all_rows) * 0.7 + 2))

    # Custom colormap: 0=red, 50=orange, 100=green, NaN=gray
    from matplotlib.colors import LinearSegmentedColormap
    cmap = LinearSegmentedColormap.from_list(
        "coverage", [(0, "#d73027"), (0.5, "#fee08b"), (1.0, "#1a9850")]
    )
    cmap.set_bad(color="#cccccc")

    im = ax.imshow(
        matrix,
        aspect="auto",
        cmap=cmap,
        vmin=0,
        vmax=100,
        interpolation="nearest",
    )

    # Annotations
    for i in range(len(matrix)):
        for j in range(len(all_fy)):
            val = matrix[i, j]
            if np.isnan(val):
                ax.text(j, i, "N/A", ha="center", va="center", fontsize=7, color="#666666")
            elif val == 0:
                ax.text(j, i, "—", ha="center", va="center", fontsize=8, color="#888888")
            else:
                color = "white" if val < 50 else "black"
                ax.text(j, i, f"{val:.0f}%", ha="center", va="center",
                        fontsize=8, fontweight="bold", color=color)

    ax.set_xticks(range(len(all_fy)))
    ax.set_xticklabels([f"FY{y}" for y in all_fy], rotation=45, ha="right", fontsize=9)
    ax.set_yticks(range(len(ylabels)))
    ax.set_yticklabels(ylabels, fontsize=9)

    # Separator line between metabolic and dental
    n_metabolic = len(metabolic_piv)
    if n_metabolic > 0 and n_metabolic < len(all_rows):
        ax.axhline(n_metabolic - 0.5, color="navy", linewidth=2, linestyle="--")

    cbar = fig.colorbar(im, ax=ax, orientation="vertical", pad=0.02, shrink=0.7)
    cbar.set_label("Prefecture coverage (%)", fontsize=9)

    ax.set_title(
        "NDB Open Data: Indicator × Fiscal Year Prefecture Coverage\n"
        "(% of 47 prefectures with observed values)",
        fontsize=11, pad=12,
    )

    fig.tight_layout()
    out_path = FIGURES_DIR / "temporal_coverage.png"
    fig.savefig(out_path, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    logger.info(f"Figure saved: {out_path}")


def figure_domain_missing_profile():
    """
    ドメイン別欠損状態積み上げ棒グラフを生成する（Figure 2）。
    Generate the domain-level missing-state stacked bar chart (Figure 2).

    Script 06 が出力した missing_suppression_profile.csv を読み込み、
    指標×欠損状態のレコード数を積み上げ棒グラフで表示する。
    左パネル: 糖尿病/メタボ系（9 指標）、右パネル: 歯科系
    各棒グラフの上部に observed 割合（%）を表示する。

    欠損状態の色分け: 緑=observed, 橙=suppressed, 紫=metric_change,
    茶=prefecture_unknown, 赤=unpublished, ピンク=parse_error, 黄=missing_unknown

    Input:  tables/missing_suppression_profile.csv
    Output: figures/domain_missing_profile.png (300 dpi)
    """
    prof_path = TABLES_DIR / "missing_suppression_profile.csv"
    if not prof_path.exists():
        logger.error(f"Profile not found: {prof_path}")
        return

    prof = pd.read_csv(prof_path, encoding="utf-8-sig")
    prof["fiscal_year"] = pd.to_numeric(prof["fiscal_year"], errors="coerce")

    STATE_COLORS = {
        "observed": "#2ca02c",
        "suppressed": "#ff7f0e",
        "metric_change": "#9467bd",
        "prefecture_unknown": "#8c564b",
        "unpublished": "#d62728",
        "parse_error": "#e377c2",
        "missing_unknown": "#bcbd22",
        "not_applicable": "#7f7f7f",
    }
    STATES = [
        "observed", "suppressed", "metric_change",
        "prefecture_unknown", "unpublished", "parse_error", "missing_unknown",
    ]

    INDICATOR_SHORT = {
        "HbA1C": "HbA1C",
        "fasting_glucose": "Fast.gluc.",
        "BMI": "BMI",
        "waist_circumference": "Waist",
        "systolic_BP": "Sys.BP",
        "diastolic_BP": "Dia.BP",
        "triglycerides": "TG",
        "LDL_cholesterol": "LDL",
        "HDL_cholesterol": "HDL",
    }

    # Aggregate per domain × indicator_name (sum across all years × sex × age)
    # Focus on total sex/age level
    agg_cols = [f"n_{s}" for s in STATES if f"n_{s}" in prof.columns]
    summary = prof.groupby(["domain", "indicator_name"])[agg_cols].sum().reset_index()

    # Separate domains
    metabolic = summary[summary["domain"] == "diabetes_metabolic"].copy()
    # Keep only canonical indicators
    INDICATOR_ORDER = [
        "HbA1C", "fasting_glucose", "BMI", "waist_circumference",
        "systolic_BP", "diastolic_BP", "triglycerides",
        "LDL_cholesterol", "HDL_cholesterol",
    ]
    metabolic = metabolic[metabolic["indicator_name"].isin(INDICATOR_ORDER)].copy()
    metabolic["sort_key"] = metabolic["indicator_name"].map(
        {ind: i for i, ind in enumerate(INDICATOR_ORDER)}
    )
    metabolic = metabolic.sort_values("sort_key")

    dental = summary[summary["domain"] == "dental_oral"].copy()

    fig, axes = plt.subplots(1, 2, figsize=(16, 7))
    fig.suptitle(
        "NDB Open Data: Missing State Distribution by Domain and Indicator\n"
        "(All releases No.1-11, all sex/age groups combined)",
        fontsize=12, y=1.01,
    )

    for ax, (domain_df, title, domain_label) in zip(
        axes,
        [
            (metabolic, "Diabetes/Metabolic Domain\n(Specific Health Checkup, FY2013-2023)", "metabolic"),
            (dental, "Dental/Oral Domain\n(Claims, FY2014-2024)", "dental"),
        ],
    ):
        if len(domain_df) == 0:
            ax.text(0.5, 0.5, "No data", ha="center", va="center", transform=ax.transAxes)
            ax.set_title(title)
            continue

        indicators = domain_df["indicator_name"].tolist()
        xlabels = [INDICATOR_SHORT.get(ind, ind[:12]) for ind in indicators]

        bottoms = np.zeros(len(indicators))
        for state in STATES:
            col = f"n_{state}"
            if col not in domain_df.columns:
                continue
            vals = domain_df[col].fillna(0).values.astype(float)
            if vals.sum() == 0:
                continue
            ax.bar(
                range(len(indicators)),
                vals,
                bottom=bottoms,
                color=STATE_COLORS.get(state, "#999999"),
                label=state,
                alpha=0.85,
            )
            bottoms += vals

        # Add percentages for observed
        obs_col = "n_observed"
        if obs_col in domain_df.columns:
            totals = bottoms.copy()
            for i, (obs_val, total_val) in enumerate(
                zip(domain_df[obs_col].fillna(0).values, totals)
            ):
                if total_val > 0:
                    pct = obs_val / total_val * 100
                    ax.text(
                        i, total_val + total_val * 0.01,
                        f"{pct:.0f}%",
                        ha="center", va="bottom", fontsize=8, color="#1a6629",
                    )

        ax.set_xticks(range(len(indicators)))
        ax.set_xticklabels(xlabels, rotation=45, ha="right", fontsize=9)
        ax.set_ylabel("Number of records", fontsize=10)
        ax.set_title(title, fontsize=10)
        ax.legend(
            loc="upper right",
            fontsize=8,
            title="Missing state",
            title_fontsize=8,
            framealpha=0.8,
        )
        ax.yaxis.grid(True, alpha=0.3)
        ax.set_axisbelow(True)

    fig.tight_layout()
    out_path = FIGURES_DIR / "domain_missing_profile.png"
    fig.savefig(out_path, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    logger.info(f"Figure saved: {out_path}")


def main():
    logger.info("=== Generating Figures ===")

    logger.info("\n--- Figure 1: Temporal Coverage Heatmap ---")
    figure_temporal_coverage()

    logger.info("\n--- Figure 2: Domain Missing Profile ---")
    figure_domain_missing_profile()

    logger.info("=== Figures complete ===")


if __name__ == "__main__":
    main()
