"""
Unit/Title audit for HbA1C and other metabolic items across all 11 NDB releases.
Output: metadata/unit_title_audit.csv

Checks:
- HbA1C item label (explicit NGSP vs implicit)
- Unit row content for each release
- Ambiguity flag

Security rules:
  - Read raw files ONLY; never write to raw/
  - Do not invent data
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
    優先順位:
      1. "受診時年齢" + "都道府県別" (No.1 のみ 2 ファイルある)
      2. "都道府県別性年齢" を含む (No.10/11 用)
      3. "※1" / "01_公費レセプトを含まない" を含む
      4. 最初に見つかったもの
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
    """1リリースのHbA1Cタイトル/単位情報を抽出"""
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
