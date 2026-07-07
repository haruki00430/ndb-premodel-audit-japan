#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
HbA1C Unit and Label Audit across NDB Open Data Releases No.1-No.11
NDB オープンデータ全リリースの HbA1C 単位・ラベル監査スクリプト

Output / 出力:
  metadata/unit_title_audit.csv — リリースごとの HbA1C 表記・単位情報（11 行）

What this script does / このスクリプトの目的:
  HbA1C には NGSP 値（%）と JDS 値（%）の 2 つの測定単位がある。
  2013 年 4 月に日本では NGSP への移行が完了しているが、
  NDB No.6 以降では Excel ファイル上の "(NGSP)[%]" の明示表記が
  無断で削除されているため、単位の一貫性を確認する必要がある。
  本スクリプトは全 11 リリースについて：
    - HbA1C 項目ラベルの表記（NGSP 明示 vs 暗黙 vs JDS）
    - 単位行の内容
    - 曖昧性フラグ
  を記録し、JDS ラベルが検出された場合は Stop Condition を発動する。

Stop Condition / 停止条件:
  JDS ラベルが 1 件でも検出された場合 → 解析を停止してユーザーに報告する。
  本スクリプトの実行結果では JDS 検出ゼロ（Stop Condition 未発動）。

Security rules / セキュリティルール:
  - Read raw files ONLY; never write to raw/ / raw/ は読み取り専用
  - Do not invent data / データを捏造しない
"""

import os
import sys
import logging
import csv
from pathlib import Path

import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings("ignore")

SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
RAW_BASE = PROJECT_DIR.parents[1] / "02_Data" / "raw" / "NDB_OpenData"
META_DIR = PROJECT_DIR / "metadata"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

RELEASE_TO_CHECKUP_FY = {
    1: 2013, 2: 2014, 3: 2015, 4: 2016, 5: 2017,
    6: 2018, 7: 2019, 8: 2020, 9: 2021, 10: 2022, 11: 2023,
}


def find_mean_values_file(release_no: int) -> Path:
    """
    各項目の平均値 都道府県別ファイルを返す。
    Find the per-item mean values file (prefecture-level) for a given release.

    優先順位 / Priority order:
      1. "受診時年齢" + "都道府県別"  — No.1 のみ 2 ファイル存在するため受診時年齢を優先
      2. "都道府県別性年齢" を含む   — No.10/11 のファイル構造再編後の主ファイル
      3. "※1" / "01_公費レセプトを含まない" を含む — 公費なし版を優先
      4. 最初に見つかったもの        — 上記に該当しない場合のフォールバック

    Args:
        release_no: NDB リリース番号（1〜11）

    Returns:
        Path: 対象ファイルのパス。見つからない場合は None。
    """
    base = RAW_BASE / f"No.{release_no}" / "07_特定健診 検査"
    if not base.exists():
        return None
    candidates = []
    for root, dirs, files in os.walk(base):
        for f in files:
            if "各項目" in f and "平均値" in f and "都道府県別" in f and f.endswith(".xlsx"):
                candidates.append(Path(root) / f)

    if not candidates:
        return None

    # 優先1: 受診時年齢
    for c in candidates:
        if "受診時年齢" in str(c):
            return c

    # 優先2: 都道府県別性年齢 (No.10/11で有効)
    for c in candidates:
        if "都道府県別性年齢" in str(c):
            return c

    # 優先3: 公費なし
    for c in candidates:
        if "※1" in str(c) or "01_公費" in str(c):
            return c

    return candidates[0]


def audit_release(release_no: int) -> dict:
    """
    1 リリースの HbA1C タイトル・単位情報を抽出する。
    Audit HbA1C item label and unit notation for a single NDB release.

    Args:
        release_no: NDB リリース番号（1〜11）

    Returns:
        dict: 以下のキーを持つ監査結果レコード
            release_no, fiscal_year_checkup, source_file, source_subdir,
            title_row_text, hba1c_item_label, hba1c_item_row,
            unit_row_content, explicit_ngsp, explicit_jds,
            explicit_percent, ambiguous_unit, notes
    """
    fpath = find_mean_values_file(release_no)
    checkup_fy = RELEASE_TO_CHECKUP_FY[release_no]

    if fpath is None:
        return {
            "release_no": release_no,
            "fiscal_year_checkup": checkup_fy,
            "source_file": "NOT_FOUND",
            "source_subdir": "NOT_FOUND",
            "title_row_text": "NOT_FOUND",
            "hba1c_item_label": "NOT_FOUND",
            "hba1c_item_row": -1,
            "unit_row_content": "NOT_FOUND",
            "explicit_ngsp": False,
            "explicit_jds": False,
            "explicit_percent": False,
            "ambiguous_unit": True,
            "notes": "File not found",
        }

    try:
        df = pd.read_excel(fpath, header=None, dtype=str)
    except Exception as e:
        return {
            "release_no": release_no,
            "fiscal_year_checkup": checkup_fy,
            "source_file": fpath.name,
            "source_subdir": str(fpath.parent.name),
            "title_row_text": f"READ_ERROR: {e}",
            "hba1c_item_label": "READ_ERROR",
            "hba1c_item_row": -1,
            "unit_row_content": "READ_ERROR",
            "explicit_ngsp": False,
            "explicit_jds": False,
            "explicit_percent": False,
            "ambiguous_unit": True,
            "notes": f"Excel read error: {e}",
        }

    title_text = str(df.iloc[0, 0]).strip() if len(df) > 0 and pd.notna(df.iloc[0, 0]) else "N/A"

    # Unit row (Row 4)
    unit_row_vals = []
    if len(df) > 4:
        unit_row_vals = [str(x).strip() for x in df.iloc[4, :] if pd.notna(x) and str(x).strip() != "nan"]
    unit_row_content = " | ".join(unit_row_vals[:6])

    # HbA1C item label
    hba1c_label = None
    hba1c_row_idx = -1
    for ri in range(5, min(60, len(df))):
        cell = str(df.iloc[ri, 1]).strip() if pd.notna(df.iloc[ri, 1]) else ""
        if "HbA1" in cell or "hba1" in cell.lower():
            hba1c_label = cell
            hba1c_row_idx = ri
            break

    explicit_ngsp = hba1c_label is not None and "NGSP" in hba1c_label
    explicit_jds = hba1c_label is not None and "JDS" in hba1c_label
    explicit_percent = hba1c_label is not None and ("%" in hba1c_label or "[%]" in hba1c_label)
    # Ambiguous = found item but no explicit NGSP marker
    ambiguous_unit = hba1c_label is not None and not explicit_ngsp and not explicit_jds

    notes_parts = []
    if hba1c_label is None:
        notes_parts.append("HbA1C item not found in rows 5-60")
    if explicit_ngsp:
        notes_parts.append("NGSP explicitly labeled in item name")
    if ambiguous_unit:
        notes_parts.append("HbA1C found but no explicit NGSP/JDS label; assumed NGSP per transition policy")
    if explicit_jds:
        notes_parts.append("WARNING: JDS label found — unit conflict!")

    return {
        "release_no": release_no,
        "fiscal_year_checkup": checkup_fy,
        "source_file": fpath.name,
        "source_subdir": str(fpath.parent.name)[:60],
        "title_row_text": title_text,
        "hba1c_item_label": hba1c_label if hba1c_label else "NOT_FOUND",
        "hba1c_item_row": hba1c_row_idx,
        "unit_row_content": unit_row_content if unit_row_content else "N/A",
        "explicit_ngsp": explicit_ngsp,
        "explicit_jds": explicit_jds,
        "explicit_percent": explicit_percent,
        "ambiguous_unit": ambiguous_unit,
        "notes": "; ".join(notes_parts) if notes_parts else "OK",
    }


def main():
    logger.info("=== Unit/Title Audit: HbA1C across NDB releases No.1-11 ===")
    rows = []
    for release_no in range(1, 12):
        r = audit_release(release_no)
        rows.append(r)
        logger.info(
            f"No.{release_no} FY{r['fiscal_year_checkup']}: "
            f"label={r['hba1c_item_label']!r}  explicit_ngsp={r['explicit_ngsp']}  "
            f"ambiguous={r['ambiguous_unit']}"
        )

    out_path = META_DIR / "unit_title_audit.csv"
    fieldnames = [
        "release_no", "fiscal_year_checkup", "source_file", "source_subdir",
        "title_row_text", "hba1c_item_label", "hba1c_item_row",
        "unit_row_content", "explicit_ngsp", "explicit_jds", "explicit_percent",
        "ambiguous_unit", "notes",
    ]
    with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    logger.info(f"Output: {out_path} ({len(rows)} rows)")

    # Summary
    n_explicit = sum(1 for r in rows if r["explicit_ngsp"])
    n_ambiguous = sum(1 for r in rows if r["ambiguous_unit"])
    n_jds = sum(1 for r in rows if r["explicit_jds"])
    logger.info(f"Summary: explicit_ngsp={n_explicit}, ambiguous={n_ambiguous}, jds_conflict={n_jds}")
    if n_jds > 0:
        logger.error("STOP CONDITION: JDS label found — unit conflict. Report before proceeding.")
    else:
        logger.info("No JDS conflict detected. No Stop Condition triggered.")


if __name__ == "__main__":
    main()
