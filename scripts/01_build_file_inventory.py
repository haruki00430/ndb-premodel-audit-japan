#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
NDB Open Data File Inventory Builder
ファイルインベントリ構築スクリプト

Builds / 出力:
  metadata/ndb_file_inventory.csv   — 全 3,137 ファイルのメタデータ一覧
  metadata/ndb_release_year_map.csv — リリース番号 × レセプト/特定健診年度マップ

What this script does / このスクリプトの目的:
  NDB Open Data No.1-No.11 の全 Excel ファイルを再帰的に列挙し、
  ファイル名から地理的集計単位・性別・年齢情報の有無を推定して CSV に記録する。
  データを読み込まず、ファイルの存在とメタデータのみを記録する。

Security rules / セキュリティルール:
  - Do not overwrite raw files / raw/ 内のファイルを書き換えない
  - Do not invent data / データを捏造しない
  - Record missing states separately / 欠損状態は種別ごとに記録する
    (suppressed / unpublished / not_applicable / missing_unknown / parse_error)
"""

import os
import sys
import csv
import logging
from pathlib import Path

# ── パス設定 ──────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
RAW_BASE = PROJECT_DIR.parents[1] / "02_Data" / "raw" / "NDB_OpenData"
META_DIR = PROJECT_DIR / "metadata"
META_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(PROJECT_DIR / "metadata" / "build_inventory.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

# ── NDB リリース年度マップ（厚労省公表情報に基づく既知情報） ────────────────────
# レセプト年度 / 特定健診年度 は NDB 公表ページ・解説編PDFより
RELEASE_YEAR_MAP = [
    # (release_no, claims_fy, checkup_fy, release_date_note)
    (1,  2014, 2013, "2015年度公表（FY2014レセプト・FY2013特定健診）"),
    (2,  2015, 2014, "2016年度公表（FY2015レセプト・FY2014特定健診）"),
    (3,  2016, 2015, "2017年度公表（FY2016レセプト・FY2015特定健診）"),
    (4,  2017, 2016, "2018年度公表（FY2017レセプト・FY2016特定健診）"),
    (5,  2018, 2017, "2019年度公表（FY2018レセプト・FY2017特定健診）"),
    (6,  2019, 2018, "2020年度公表（FY2019レセプト・FY2018特定健診）"),
    (7,  2020, 2019, "2021年度公表（FY2020レセプト・FY2019特定健診）"),
    (8,  2021, 2020, "2022年度公表（FY2021レセプト・FY2020特定健診）"),
    (9,  2022, 2021, "2023年度公表（FY2022レセプト・FY2021特定健診）"),
    (10, 2023, 2022, "2024年度公表（FY2023レセプト・FY2022特定健診）"),
    (11, 2024, 2023, "2025年度公表（FY2024レセプト・FY2023特定健診）"),
]

# ── カテゴリ分類マッピング ──────────────────────────────────────────────────
CATEGORY_MAP = {
    "01_医科診療行為（患者数）": "medical_acts_patients",
    "01_医科診療行為（算定回数）": "medical_acts_count",
    "02_歯科診療行為（患者数）": "dental_acts_patients",
    "02_歯科診療行為（算定回数）": "dental_acts_count",
    "03_調剤行為（患者数）": "dispensing_patients",
    "03_調剤行為（算定回数）": "dispensing_count",
    "04_歯科傷病": "dental_diseases",
    "05_処方薬": "prescriptions",
    "06_特定保険医療材料": "medical_materials",
    "07_特定健診 検査": "health_checkup_exam",
    "07_特定健診 質問票": "health_checkup_questionnaire",
}


def detect_geographic_level(filename: str) -> str:
    """
    ファイル名から地理的集計単位を判定する。
    Infer the geographic aggregation level from the Excel filename.

    Args:
        filename: NDB Excel ファイル名

    Returns:
        str: "prefecture" / "secondary_medical_area" / "national" /
             "sex_age_national" / "unknown" のいずれか
    """
    fn = filename
    if "都道府県別" in fn:
        return "prefecture"
    elif "二次医療圏別" in fn:
        return "secondary_medical_area"
    elif "全国" in fn or "全国別" in fn:
        return "national"
    elif "性年齢別" in fn or "性年齢階級別" in fn:
        return "sex_age_national"
    else:
        return "unknown"


def detect_sex_age_availability(filename: str) -> tuple:
    """
    ファイル名から性別・年齢情報の有無を判定する。
    Infer whether sex and age stratification are available from the filename.

    Args:
        filename: NDB Excel ファイル名

    Returns:
        tuple[bool, bool]: (has_sex, has_age) — ファイル名に「性」「男/女」「年齢」「階級」が含まれるか
    """
    has_sex = "性" in filename and ("男" in filename or "女" in filename or "性年齢" in filename or "性別" in filename)
    has_age = "年齢" in filename or "階級" in filename
    return has_sex, has_age


def get_xlsx_files_recursive(folder: Path, release_no: int) -> list:
    """
    指定フォルダ配下の Excel ファイルを再帰的に列挙する。
    Recursively enumerate all Excel files under the given NDB release folder.

    ファイルは読み込まない（スキーマ・パス情報のみ記録）。

    Args:
        folder: 対象フォルダ（例: No.1 の root）
        release_no: NDB リリース番号（1〜11）

    Returns:
        list[dict]: ファイルごとのメタデータレコード（地理単位・性別・年齢の有無を含む）
    """
    records = []
    if not folder.exists():
        return records
    for root, dirs, files in os.walk(folder):
        root_path = Path(root)
        for f in files:
            if f.endswith(".xlsx") or f.endswith(".xls"):
                fp = root_path / f
                rel_path = fp.relative_to(RAW_BASE / f"No.{release_no}")
                parts = rel_path.parts
                category = parts[0] if parts else "unknown"
                data_type = CATEGORY_MAP.get(category, "other")
                geo_level = detect_geographic_level(f)
                has_sex, has_age = detect_sex_age_availability(f)
                # ファイルサイズで存在確認（rawファイルは開かない）
                try:
                    fsize = fp.stat().st_size
                    file_status = "exists"
                except Exception:
                    fsize = 0
                    file_status = "parse_error"
                records.append({
                    "release_no": release_no,
                    "data_type": data_type,
                    "category": category,
                    "subfolder": str(Path(*parts[1:-1])) if len(parts) > 2 else "",
                    "file_name": f,
                    "relative_path": str(rel_path),
                    "file_size_bytes": fsize,
                    "file_status": file_status,
                    "geographic_level_detected": geo_level,
                    "sex_available": "yes" if has_sex else "unknown",
                    "age_available": "yes" if has_age else "unknown",
                    "notes": "",
                })
    return records


def build_file_inventory():
    """
    NDB No.1〜11 の全ファイルインベントリを構築して CSV に書き出す。
    Build and export the complete file inventory for NDB Open Data releases No.1-11.

    Returns:
        list[dict]: 3,137 件のファイルメタデータレコード
    """
    logger.info("=== ファイルインベントリ構築開始 ===")
    all_records = []

    for rel_no in range(1, 12):
        release_dir = RAW_BASE / f"No.{rel_no}"
        if not release_dir.exists():
            logger.warning(f"No.{rel_no} フォルダが存在しません: {release_dir}")
            continue
        logger.info(f"No.{rel_no} を処理中...")
        records = get_xlsx_files_recursive(release_dir, rel_no)
        logger.info(f"  → {len(records)} ファイルを検出")
        all_records.extend(records)

    # CSV 書き出し
    out_path = META_DIR / "ndb_file_inventory.csv"
    fieldnames = [
        "release_no", "data_type", "category", "subfolder",
        "file_name", "relative_path", "file_size_bytes", "file_status",
        "geographic_level_detected", "sex_available", "age_available", "notes",
    ]
    with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_records)

    logger.info(f"ファイルインベントリ書き出し完了: {out_path} ({len(all_records)} 行)")
    return all_records


def build_release_year_map():
    """
    リリース番号 × 年度マップを CSV に書き出す。
    Export the release-number to fiscal-year mapping table.

    RELEASE_YEAR_MAP 定数（厚労省公表情報に基づく）を CSV 形式で保存する。
    構造的変化フラグ（二次医療圏追加: No.6〜, フォルダ再編: No.10〜）も記録する。

    Returns:
        list[dict]: 11 行のリリース年度マップ
    """
    logger.info("=== リリース年度マップ構築 ===")
    out_path = META_DIR / "ndb_release_year_map.csv"
    fieldnames = [
        "release_no", "claims_fiscal_year", "specific_health_checkup_fiscal_year",
        "release_date_if_known", "source_url_or_note",
        "questionnaire_available", "secondary_medical_area_added",
        "public_fee_exclusion_restructured",
    ]
    rows = []
    for (rel_no, claims_fy, checkup_fy, note) in RELEASE_YEAR_MAP:
        # 構造的変化を記録
        questionnaire = "no" if rel_no == 1 else "yes"
        secondary_medical = "yes" if rel_no >= 6 else "no"
        restructured = "yes" if rel_no >= 10 else "no"
        rows.append({
            "release_no": rel_no,
            "claims_fiscal_year": claims_fy,
            "specific_health_checkup_fiscal_year": checkup_fy,
            "release_date_if_known": note,
            "source_url_or_note": "厚生労働省NDBオープンデータ公表ページ",
            "questionnaire_available": questionnaire,
            "secondary_medical_area_added": secondary_medical,
            "public_fee_exclusion_restructured": restructured,
        })
    with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    logger.info(f"リリース年度マップ書き出し完了: {out_path}")
    return rows


def print_summary(all_records):
    """サマリーをログ出力"""
    from collections import Counter
    by_release = Counter(r["release_no"] for r in all_records)
    by_type = Counter(r["data_type"] for r in all_records)
    logger.info("=== サマリー ===")
    logger.info(f"総ファイル数: {len(all_records)}")
    for rel_no in sorted(by_release):
        logger.info(f"  No.{rel_no}: {by_release[rel_no]} ファイル")
    logger.info("データ種別内訳:")
    for dtype, cnt in sorted(by_type.items(), key=lambda x: -x[1]):
        logger.info(f"  {dtype}: {cnt}")


if __name__ == "__main__":
    all_records = build_file_inventory()
    build_release_year_map()
    print_summary(all_records)
    logger.info("=== 完了 ===")
