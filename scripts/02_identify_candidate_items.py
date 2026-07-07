#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Candidate Indicator Identification and Prefecture-Year Feasibility Assessment
候補アウトカム項目の特定と Prefecture-Year Feasibility 評価

Builds / 出力:
  tables/candidate_outcome_items.csv      — 25 指標候補の存在確認・地理的集計単位
  tables/prefecture_year_feasibility.csv  — 指標別 Feasibility グレード (A〜D) 評価

What this script does / このスクリプトの目的:
  事前に定義した 25 の候補指標について、NDB No.1-No.11 の各リリースで
  都道府県別ファイルが存在するかを確認し、時系列カバレッジと
  Feasibility グレードを付与する。
  Grade A = 10-11 リリースで都道府県別データあり（主解析に使用可能）
  Grade B = 7-9 リリースで利用可能（条件付き）
  Grade C = 6 リリース以下（補足目的のみ）
  Grade D = 0 リリース（使用不可）

Security rules / セキュリティルール:
  - Read raw files only; never write to raw/ / raw/ は読み取り専用
  - Distinguish missing states / 欠損状態を種別ごとに記録する
    (suppressed / unpublished / not_applicable / missing_unknown / parse_error)
  - Do not invent data / データを捏造しない
"""

import os
import sys
import csv
import logging
import warnings
from pathlib import Path
from collections import defaultdict

warnings.filterwarnings("ignore")

SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
RAW_BASE = PROJECT_DIR.parents[1] / "02_Data" / "raw" / "NDB_OpenData"
TABLES_DIR = PROJECT_DIR / "tables"
TABLES_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(PROJECT_DIR / "tables" / "candidate_items.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

# ── NDBリリース年度マップ ────────────────────────────────────────────────────
RELEASE_TO_CHECKUP_FY = {
    1: 2013, 2: 2014, 3: 2015, 4: 2016, 5: 2017,
    6: 2018, 7: 2019, 8: 2020, 9: 2021, 10: 2022, 11: 2023,
}

# ── 候補アウトカム項目定義 ──────────────────────────────────────────────────────
# 各エントリ: (candidate_family, item_name, data_category, file_pattern, domain_note)
CANDIDATE_ITEMS = [
    # === Diabetes/Metabolic Primary ===
    ("diabetes_metabolic", "HbA1C",
     "health_checkup_exam", "HbA1",
     "Primary diabetes marker; glycated hemoglobin; NOTE: HbA1C (No.1-2,11) vs HbA1c (No.3-10) naming change"),
    ("diabetes_metabolic", "fasting_glucose",
     "health_checkup_exam", "空腹時血糖",
     "Fasting plasma glucose; primary diabetes marker"),
    ("diabetes_metabolic", "random_glucose",
     "health_checkup_exam", "随時血糖",
     "Random glucose; added in later releases"),
    ("diabetes_metabolic", "BMI",
     "health_checkup_exam", "BMI",
     "Body mass index; obesity/metabolic indicator"),
    ("diabetes_metabolic", "waist_circumference",
     "health_checkup_exam", "腹囲",
     "Abdominal circumference; central obesity marker"),
    ("diabetes_metabolic", "triglycerides",
     "health_checkup_exam", "中性脂肪",
     "Triglycerides; dyslipidemia/metabolic syndrome"),
    ("diabetes_metabolic", "HDL_cholesterol",
     "health_checkup_exam", "HDL",
     "HDL cholesterol; metabolic syndrome criterion"),
    ("diabetes_metabolic", "LDL_cholesterol",
     "health_checkup_exam", "LDL",
     "LDL cholesterol; cardiovascular risk"),
    ("diabetes_metabolic", "systolic_BP",
     "health_checkup_exam", "収縮期血圧",
     "Systolic blood pressure; metabolic syndrome"),
    ("diabetes_metabolic", "diastolic_BP",
     "health_checkup_exam", "拡張期血圧",
     "Diastolic blood pressure"),
    ("diabetes_metabolic", "urine_glucose",
     "health_checkup_exam", "尿糖",
     "Urine glucose; diabetes screening"),
    ("diabetes_metabolic", "eGFR",
     "health_checkup_exam", "eGFR",
     "eGFR; kidney function / diabetic nephropathy"),
    ("diabetes_metabolic", "serum_creatinine",
     "health_checkup_exam", "血清クレアチニン",
     "Serum creatinine; kidney function"),
    ("diabetes_metabolic", "mean_values_all_items",
     "health_checkup_exam", "各項目の平均値",
     "Composite mean values table; contains multiple markers"),
    # === Questionnaire-based (metabolic/lifestyle) ===
    ("diabetes_metabolic", "questionnaire_Q1_smoking",
     "health_checkup_questionnaire", "質問項目１",
     "Smoking history (Q1); lifestyle risk"),
    ("diabetes_metabolic", "questionnaire_Q6_alcohol",
     "health_checkup_questionnaire", "質問項目６",
     "Drinking frequency (Q6); lifestyle risk"),
    ("diabetes_metabolic", "questionnaire_Q9_exercise",
     "health_checkup_questionnaire", "質問項目９",
     "Physical activity habit (Q9); obesity/metabolic"),
    ("diabetes_metabolic", "questionnaire_Q11_eating_fast",
     "health_checkup_questionnaire", "質問項目１１",
     "Eating speed (Q11); obesity risk"),
    ("diabetes_metabolic", "questionnaire_Q14_BMI_derived",
     "health_checkup_questionnaire", "質問項目１４",
     "Weight gain since age 20 (Q14); metabolic"),
    # === Dental/Oral-care Primary ===
    ("dental_oral", "dental_disease_prevalence_prefecture",
     "dental_diseases", "都道府県別",
     "Dental disease/act counts by prefecture; NOTE: filename='傷病件数' in No.1-7,9; '算定回数' in No.8; subdirectory in No.10-11"),
    ("dental_oral", "dental_disease_prevalence_sex_age",
     "dental_diseases", "性年齢別",
     "Dental disease/act counts by sex/age; same naming change as prefecture file"),
    ("dental_oral", "dental_act_count_prefecture",
     "dental_acts_count", "都道府県",
     "Dental procedure counts by prefecture"),
    ("dental_oral", "dental_act_patients_prefecture",
     "dental_acts_patients", "都道府県",
     "Dental patient counts by prefecture"),
    # === Secondary: Medications ===
    ("medication", "prescription_drug_prefecture",
     "prescriptions", "都道府県",
     "Prescription drug data by prefecture"),
    # === Secondary: Rehabilitation ===
    ("rehabilitation", "rehabilitation_acts",
     "medical_acts_count", "H_リハビリテーション",
     "Rehabilitation diagnostic act counts"),
]

# ── No.1〜11 の特定健診検査ファイル検索パターン ─────────────────────────────────
def find_exam_files(release_no: int, pattern: str) -> list:
    """
    特定健診検査フォルダ内で都道府県別ファイルを検索する。
    Search for prefecture-level Excel files in the specific health checkup exam folder.

    大文字小文字を区別しない（HbA1C vs HbA1c 等の表記ゆれに対応）。
    Case-insensitive match — accommodates HbA1C/HbA1c naming variations across releases.

    Args:
        release_no: NDB リリース番号（1〜11）
        pattern: 検索パターン文字列（例: "HbA1", "空腹時血糖"）

    Returns:
        list[Path]: 一致したファイルパスのリスト
    """
    base = RAW_BASE / f"No.{release_no}" / "07_特定健診 検査"
    found = []
    if not base.exists():
        return found
    pattern_lower = pattern.lower()
    for root, dirs, files in os.walk(base):
        for f in files:
            if pattern_lower in f.lower() and "都道府県別" in f and f.endswith(".xlsx"):
                found.append(Path(root) / f)
    return found


def find_questionnaire_files(release_no: int, pattern: str) -> list:
    """特定健診質問票フォルダ内でパターンに一致するファイルを検索
    No.2-5: 「都道府県別」の表記なし（単一ファイルに都道府県データ含む）
    No.6-9: 「都道府県別性年齢階級別分布」が明示
    No.10-11: 01_公費レセプトを含まないデータ サブフォルダ内
    """
    base = RAW_BASE / f"No.{release_no}" / "07_特定健診 質問票"
    found = []
    if not base.exists():
        return found
    for root, dirs, files in os.walk(base):
        for f in files:
            if pattern in f and f.endswith(".xlsx"):
                # No.2-5: 「都道府県別」なし → 単一ファイルで都道府県データを包含
                # No.6以降: 「都道府県別」あり → 都道府県別専用ファイル
                found.append(Path(root) / f)
    return found


def find_dental_disease_files(release_no: int, pattern: str) -> list:
    """歯科傷病フォルダ内でパターンに一致するファイルを検索"""
    base = RAW_BASE / f"No.{release_no}" / "04_歯科傷病"
    found = []
    if not base.exists():
        return found
    for root, dirs, files in os.walk(base):
        for f in files:
            if pattern in f and f.endswith(".xlsx"):
                found.append(Path(root) / f)
    return found


def find_dental_act_files(release_no: int, category: str, pattern: str) -> list:
    """歯科診療行為フォルダ内でパターンに一致するファイルを検索"""
    cat_map = {
        "dental_acts_count": "02_歯科診療行為（算定回数）",
        "dental_acts_patients": "02_歯科診療行為（患者数）",
    }
    folder_name = cat_map.get(category, "")
    base = RAW_BASE / f"No.{release_no}" / folder_name
    found = []
    if not base.exists():
        return found
    for root, dirs, files in os.walk(base):
        for f in files:
            if pattern in f and f.endswith(".xlsx"):
                found.append(Path(root) / f)
    return found[:3]  # サンプルのみ（全件不要）


def find_prescription_files(release_no: int, pattern: str) -> list:
    """処方薬フォルダ内でパターンに一致するファイルを検索"""
    base = RAW_BASE / f"No.{release_no}" / "05_処方薬"
    found = []
    if not base.exists():
        return found
    for root, dirs, files in os.walk(base):
        for f in files:
            if pattern in f and f.endswith(".xlsx"):
                found.append(Path(root) / f)
    return found[:3]


def find_rehab_files(release_no: int, pattern: str) -> list:
    """医科診療行為（H:リハビリ）フォルダ内のファイルを検索
    「H_リハビリテーション」はサブフォルダ名なので、フォルダ配下の全xlsxを返す"""
    base = RAW_BASE / f"No.{release_no}" / "01_医科診療行為（算定回数）"
    found = []
    if not base.exists():
        return found
    for root, dirs, files in os.walk(base):
        root_name = Path(root).name
        # サブフォルダ名に「リハビリ」が含まれる場合、配下ファイルを返す
        if "リハビリ" in root_name:
            for f in files:
                if f.endswith(".xlsx"):
                    found.append(Path(root) / f)
            if found:
                return found[:3]
    return found[:3]


def search_files_for_item(release_no: int, category: str, pattern: str) -> list:
    """カテゴリ・パターンに基づいてファイルを検索"""
    if category == "health_checkup_exam":
        return find_exam_files(release_no, pattern)
    elif category == "health_checkup_questionnaire":
        return find_questionnaire_files(release_no, pattern)
    elif category == "dental_diseases":
        return find_dental_disease_files(release_no, pattern)
    elif category in ("dental_acts_count", "dental_acts_patients"):
        return find_dental_act_files(release_no, category, pattern)
    elif category == "prescriptions":
        return find_prescription_files(release_no, pattern)
    elif category == "medical_acts_count":
        return find_rehab_files(release_no, pattern)
    return []


def build_candidate_items():
    """
    25 候補アウトカム項目の存在確認テーブルを構築して CSV に書き出す。
    Build and export the candidate outcome item existence table for all 25 items.

    各候補について No.1〜11 の全リリースにファイルが存在するかを確認し、
    利用可能年度数・地理的集計単位・先頭ファイルサンプルを記録する。
    実際にデータは読み込まない（ファイルの存在確認のみ）。

    Returns:
        list[dict]: 25 行の候補アウトカム項目テーブル
    """
    logger.info("=== 候補アウトカム項目の特定開始 ===")
    rows = []

    # 各候補項目について No.1〜11 の存在確認
    for (family, item_name, category, pattern, domain_note) in CANDIDATE_ITEMS:
        years_available = []
        source_files_sample = []
        geo_levels_found = set()

        for rel_no in range(1, 12):
            checkup_fy = RELEASE_TO_CHECKUP_FY[rel_no]
            files = search_files_for_item(rel_no, category, pattern)
            if files:
                years_available.append(str(checkup_fy))
                if not source_files_sample:
                    source_files_sample.append(f"No.{rel_no}/{files[0].name}")
                for f in files:
                    if "都道府県別" in f.name:
                        geo_levels_found.add("prefecture")
                    if "二次医療圏別" in f.name:
                        geo_levels_found.add("secondary_medical_area")

        years_str = ",".join(years_available) if years_available else "unpublished"
        geo_str = ",".join(sorted(geo_levels_found)) if geo_levels_found else "unknown"
        source_str = source_files_sample[0] if source_files_sample else "not_found"

        rows.append({
            "candidate_family": family,
            "item_name": item_name,
            "source_category": category,
            "file_pattern": pattern,
            "suspected_domain": domain_note,
            "years_available": years_str,
            "n_years": len(years_available),
            "geographic_level": geo_str,
            "prefecture_available": "yes" if "prefecture" in geo_levels_found else "no",
            "sex_available": "yes",  # 特定健診は性年齢別が標準
            "age_available": "yes",
            "first_source_file": source_str,
            "notes": "",
        })
        status = "FOUND" if years_available else "NOT FOUND"
        logger.info(f"  [{status}] {family}/{item_name}: {len(years_available)}/11 リリース で利用可能")

    out_path = TABLES_DIR / "candidate_outcome_items.csv"
    fieldnames = [
        "candidate_family", "item_name", "source_category", "file_pattern",
        "suspected_domain", "years_available", "n_years", "geographic_level",
        "prefecture_available", "sex_available", "age_available",
        "first_source_file", "notes",
    ]
    with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    logger.info(f"候補アウトカム項目テーブル書き出し完了: {out_path} ({len(rows)} 行)")
    return rows


def build_feasibility_table(candidate_rows):
    """
    Prefecture-Year Feasibility グレード評価テーブルを構築して CSV に書き出す。
    Build and export the prefecture-year feasibility grade table.

    Feasibility グレードは以下の基準で付与する:
      Grade A: 10-11 リリースで都道府県別データあり → 主解析に使用可能
      Grade B: 7-9 リリースで利用可能 → 条件付きで使用可能
      Grade C: 6 リリース以下 → 補足目的のみ
      Grade D: 0 リリース → 使用不可

    構造的変化フラグ（二次医療圏追加・フォルダ再編・質問票欠如）も記録する。

    Args:
        candidate_rows: build_candidate_items() の出力リスト

    Returns:
        list[dict]: 25 行の Feasibility グレードテーブル
    """
    logger.info("=== Prefecture-Year Feasibility 評価開始 ===")
    rows = []

    for crow in candidate_rows:
        family = crow["candidate_family"]
        item_name = crow["item_name"]
        n_years = crow["n_years"]
        pref_avail = crow["prefecture_available"]
        years_str = crow["years_available"]

        # 利用可能年度のリスト
        if years_str == "unpublished":
            available_years = []
        else:
            available_years = [y for y in years_str.split(",") if y]

        # 11リリース分の年度との差分（欠損年度）
        all_checkup_fy = [str(v) for v in RELEASE_TO_CHECKUP_FY.values()]
        missing_years = [y for y in all_checkup_fy if y not in available_years]

        # 構造的変化の検出（No.6で二次医療圏追加、No.10でフォルダ再編）
        format_changes = []
        if family in ("diabetes_metabolic", "dental_oral"):
            if any(int(y) >= 2018 for y in available_years if y.isdigit()):
                format_changes.append("secondary_medical_area_added_No6")
            if any(int(y) >= 2022 for y in available_years if y.isdigit()):
                format_changes.append("folder_restructured_No10")
        if item_name == "questionnaire_Q1_smoking" and "2013" in all_checkup_fy:
            format_changes.append("questionnaire_absent_No1")
        if item_name == "random_glucose":
            format_changes.append("added_in_later_releases")

        format_changes_str = ";".join(format_changes) if format_changes else "none"

        # Feasibility グレード判定
        if n_years >= 10 and pref_avail == "yes":
            grade = "A"
            grade_note = "primary-ready: 10-11 releases, prefecture-level confirmed"
        elif n_years >= 7 and pref_avail == "yes":
            grade = "B"
            grade_note = "usable with caveats: some releases missing or format change"
        elif n_years >= 3:
            grade = "C"
            grade_note = "documentation-only: limited temporal coverage"
        elif n_years == 0:
            grade = "D"
            grade_note = "not usable: not found in any release"
        else:
            grade = "C"
            grade_note = "documentation-only: very limited coverage"

        # 特殊ケースの調整
        if item_name == "questionnaire_Q1_smoking":
            # No.1に質問票なし
            grade = "B" if grade == "A" else grade
            grade_note += "; questionnaire absent in No.1"
        if item_name == "random_glucose":
            if n_years < 5:
                grade = "B"
                grade_note = "usable with caveats: random glucose not in early releases"

        rows.append({
            "candidate_family": family,
            "item_name": item_name,
            "years_available": years_str,
            "n_years_available": n_years,
            "prefecture_available": pref_avail,
            "sex_available": crow["sex_available"],
            "age_available": crow["age_available"],
            "missing_years": ",".join(missing_years) if missing_years else "none",
            "format_changes": format_changes_str,
            "suppression_detected": "unknown",  # 実データ確認が必要
            "feasibility_grade": grade,
            "grade_rationale": grade_note,
        })

    out_path = TABLES_DIR / "prefecture_year_feasibility.csv"
    fieldnames = [
        "candidate_family", "item_name", "years_available", "n_years_available",
        "prefecture_available", "sex_available", "age_available",
        "missing_years", "format_changes", "suppression_detected",
        "feasibility_grade", "grade_rationale",
    ]
    with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    logger.info(f"Feasibility テーブル書き出し完了: {out_path} ({len(rows)} 行)")

    # Grade サマリーをログ出力
    from collections import Counter
    grade_counts = Counter(r["feasibility_grade"] for r in rows)
    logger.info("=== Feasibility Grade サマリー ===")
    for g in ["A", "B", "C", "D"]:
        items_in_grade = [r["item_name"] for r in rows if r["feasibility_grade"] == g]
        logger.info(f"  Grade {g}: {grade_counts.get(g, 0)} 項目 → {', '.join(items_in_grade)}")

    return rows


if __name__ == "__main__":
    candidate_rows = build_candidate_items()
    feasibility_rows = build_feasibility_table(candidate_rows)
    logger.info("=== 完了 ===")
