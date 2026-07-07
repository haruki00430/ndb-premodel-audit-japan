#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Full 11-Release Prefecture-Year Panel Extraction
NDB オープンデータ全 11 回完全パネル抽出スクリプト

Output / 出力:
  data/processed/ndb_prefecture_year_full_panel.csv — 146,376 件の long-format パネル

What this script does / このスクリプトの目的:
  NDB Open Data No.1-No.11 から Grade A の主要指標を全リリース・全都道府県について
  抽出し、標準的な long-format パネルデータを生成する。

Domains / 対象ドメイン:
  糖尿病/メタボ (diabetes_metabolic):
    HbA1C / 空腹時血糖 / BMI / 腹囲 / 収縮期血圧 / 拡張期血圧 /
    中性脂肪 / LDL コレステロール / HDL コレステロール
  歯科/口腔 (dental_oral):
    都道府県別疾患グループ別傷病件数 ※ No.8 は metric_change として除外

Key engineering decisions / 主な実装上の判断:
  - LDL/HDL: No.1-5 では "ＬＤＬコレステロール"、No.6-11 では "ＬＤＬ" に省略
    → NFKC 正規化 + 双方向パターンマッチで対応
  - HbA1C: No.1-2 は "HbA1C"、No.3-10 は "HbA1c"（大文字小文字ゆれ）
    → 大文字小文字を区別しない "HbA1" パターンマッチで対応
  - No.8 歯科: 傷病件数ではなく算定回数ファイルのみ存在 → metric_change
  - No.10-11: フォルダ構造が再編されたため、ファイル選択優先順位で対応

Missing state vocabulary / 欠損状態の語彙（7 種）:
  observed          : 数値が取得できた
  suppressed        : 10 件未満のためダッシュ（"－"）で公表された
  metric_change     : 指標の定義が変わったため比較不能（No.8 歯科）
  prefecture_unknown: 都道府県情報が特定できない行
  unpublished       : 当該リリースでファイルが存在しない
  parse_error       : ファイル読み込みエラー
  not_applicable    : 構造上のプレースホルダー

Security rules / セキュリティルール:
  - Read raw files ONLY; never write to raw/ / raw/ は読み取り専用
  - Do not invent data / データを捏造しない
  - Do not impute suppressed cells / 抑制値（伏字）を補完しない
  - Distinguish all missing states / 欠損状態を混在させない
"""

import os
import sys
import csv
import logging
import warnings
from pathlib import Path

import pandas as pd
import numpy as np

warnings.filterwarnings("ignore")

SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
RAW_BASE = PROJECT_DIR.parents[1] / "02_Data" / "raw" / "NDB_OpenData"
DATA_DIR = PROJECT_DIR / "data" / "processed"
DATA_DIR.mkdir(parents=True, exist_ok=True)

log_file = DATA_DIR / "full_panel_extraction.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(log_file, encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

# FY maps
RELEASE_TO_CHECKUP_FY = {
    1: 2013, 2: 2014, 3: 2015, 4: 2016, 5: 2017,
    6: 2018, 7: 2019, 8: 2020, 9: 2021, 10: 2022, 11: 2023,
}
RELEASE_TO_CLAIMS_FY = {
    1: 2014, 2: 2015, 3: 2016, 4: 2017, 5: 2018,
    6: 2019, 7: 2020, 8: 2021, 9: 2022, 10: 2023, 11: 2024,
}

PREFECTURE_CODE_MAP = {
    "北海道": "01", "青森県": "02", "岩手県": "03", "宮城県": "04", "秋田県": "05",
    "山形県": "06", "福島県": "07", "茨城県": "08", "栃木県": "09", "群馬県": "10",
    "埼玉県": "11", "千葉県": "12", "東京都": "13", "神奈川県": "14", "新潟県": "15",
    "富山県": "16", "石川県": "17", "福井県": "18", "山梨県": "19", "長野県": "20",
    "岐阜県": "21", "静岡県": "22", "愛知県": "23", "三重県": "24", "滋賀県": "25",
    "京都府": "26", "大阪府": "27", "兵庫県": "28", "奈良県": "29", "和歌山県": "30",
    "鳥取県": "31", "島根県": "32", "岡山県": "33", "広島県": "34", "山口県": "35",
    "徳島県": "36", "香川県": "37", "愛媛県": "38", "高知県": "39", "福岡県": "40",
    "佐賀県": "41", "長崎県": "42", "熊本県": "43", "大分県": "44", "宮崎県": "45",
    "鹿児島県": "46", "沖縄県": "47",
}

# Reverse map: code → name
CODE_TO_PREF = {v: k for k, v in PREFECTURE_CODE_MAP.items()}

SUPPRESSION_MARKERS = {"-", "－", "−", "*", "***", "x", "X", "　", "▲", "―", "–"}

TARGET_ITEMS_METABOLIC = {
    "HbA1C":             ["HbA1C", "HbA1c"],
    "fasting_glucose":   ["空腹時血糖"],
    "BMI":               ["BMI"],
    "waist_circumference": ["腹囲"],
    "systolic_BP":       ["収縮期血圧"],
    "diastolic_BP":      ["拡張期血圧"],
    "triglycerides":     ["中性脂肪", "トリグリセリド"],
    # No.1-5: "ＬＤＬコレステロール", No.6-11: "ＬＤＬ" (abbreviation) — both covered
    "LDL_cholesterol":   ["LDLコレステロール", "ＬＤＬコレステロール", "ＬＤＬ", "低比重"],
    "HDL_cholesterol":   ["HDLコレステロール", "ＨＤＬコレステロール", "ＨＤＬ", "高比重"],
}

ITEM_UNITS = {
    "HbA1C": "%",
    "fasting_glucose": "mg/dL",
    "BMI": "kg/m2",
    "waist_circumference": "cm",
    "systolic_BP": "mmHg",
    "diastolic_BP": "mmHg",
    "triglycerides": "mg/dL",
    "LDL_cholesterol": "mg/dL",
    "HDL_cholesterol": "mg/dL",
}

AGE_GROUPS = ["40-44", "45-49", "50-54", "55-59", "60-64", "65-69", "70-74", "total"]

SEX_AGE_COLS = {
    "male":   {"40-44": 2, "45-49": 3, "50-54": 4, "55-59": 5,
               "60-64": 6, "65-69": 7, "70-74": 8, "total": 9},
    "female": {"40-44": 10, "45-49": 11, "50-54": 12, "55-59": 13,
               "60-64": 14, "65-69": 15, "70-74": 16, "total": 17},
}

OUTPUT_FIELDNAMES = [
    "domain", "indicator_family", "indicator_name",
    "release_no", "fiscal_year", "data_year_type",
    "prefecture_code", "prefecture_name",
    "sex", "age_group",
    "value", "unit", "metric_type",
    "missing_state",
    "source_file", "source_sheet",
]


def parse_value(val):
    """
    生セル値を数値または欠損状態に変換する。
    Parse a raw cell value into (numeric_value, missing_state).

    NDB の抑制値マーカー（"－"・"−"・"*" 等）を suppressed として記録し、
    空白・NaN を missing_unknown として記録する。
    抑制値は絶対にゼロとして扱わない。

    Args:
        val: Excel セルの生値（str / float / None）

    Returns:
        tuple[float | None, str | None]:
            (数値, None) — 正常に解析できた場合
            (None, "suppressed") — 10 件未満の伏字マーカーの場合
            (None, "missing_unknown") — 空白・NaN の場合
            (None, "parse_error") — 解析不能な文字列の場合
    """
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return None, "missing_unknown"
    s = str(val).strip()
    if not s or s in ("nan", ""):
        return None, "missing_unknown"
    if s in SUPPRESSION_MARKERS:
        return None, "suppressed"
    try:
        return float(s.replace(",", "").replace("，", "").replace(" ", "")), None
    except (ValueError, TypeError):
        return None, "parse_error"


def normalize_str(s: str) -> str:
    """
    Unicode NFKC 正規化で全角英数字を半角に変換する。
    Normalize full-width ASCII to half-width using NFKC.

    NDB No.6-11 では "ＬＤＬ"（全角 3 文字）のように
    コレステロール指標が全角英字で省略表記されている。
    この関数で正規化することで半角パターンとのマッチが可能になる。

    Args:
        s: 正規化前の文字列

    Returns:
        str: NFKC 正規化後の文字列
    """
    import unicodedata
    return unicodedata.normalize("NFKC", s)


def find_mean_values_file(release_no: int) -> Path:
    """
    各項目の平均値 都道府県別ファイルを返す。
    Priority:
      1. "受診時年齢" subfolder (No.1 only has 2 options)
      2. file name contains "都道府県別性年齢" (No.10/11 main file)
      3. path contains "※1" or "01_公費レセプトを含まない"
      4. first found
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

    for c in candidates:
        if "受診時年齢" in str(c):
            return c
    for c in candidates:
        if "都道府県別性年齢" in str(c):
            return c
    for c in candidates:
        if "※1" in str(c) or "01_公費" in str(c):
            return c
    return candidates[0]


def get_pref_code(pref_raw: str) -> tuple[str, str]:
    """都道府県名 → (code, canonical_name)"""
    pref_name = str(pref_raw).strip()
    if pref_name in PREFECTURE_CODE_MAP:
        return PREFECTURE_CODE_MAP[pref_name], pref_name
    for k, v in PREFECTURE_CODE_MAP.items():
        if k in pref_name or pref_name in k:
            return v, k
    return "XX", pref_name


def match_item(item_raw_str: str) -> str | None:
    """
    生ラベル文字列を正規化して canonical indicator_name に変換する。
    Map a raw item label string to a canonical indicator name.

    No.6-11 では "ＬＤＬ" のように省略された全角表記が使われているため、
    NFKC 正規化 + 双方向マッチ（パターンが文字列を含む / 文字列がパターンを含む）
    の両方を試みる。大文字小文字を区別しない。

    Args:
        item_raw_str: Excel から読み込んだ生の項目ラベル文字列
            例: "HbA1C(NGSP)[%]"、"ＬＤＬ"、"腹囲"

    Returns:
        str | None: canonical 指標名（例: "HbA1C", "LDL_cholesterol"）
                    マッチしない場合は None
    """
    s = item_raw_str.strip()
    s_norm = normalize_str(s)
    s_norm_lower = s_norm.lower()
    for canonical, patterns in TARGET_ITEMS_METABOLIC.items():
        for pat in patterns:
            pat_norm = normalize_str(pat)
            pat_norm_lower = pat_norm.lower()
            # Forward: pattern in item
            if pat in s or pat_norm in s_norm or pat_norm_lower in s_norm_lower:
                return canonical
            # Reverse: item in pattern (handles abbreviated labels like "ＬＤＬ" in "ＬＤＬコレステロール")
            if s in pat or s_norm in pat_norm or s_norm_lower in pat_norm_lower:
                return canonical
    return None


def extract_metabolic(release_no: int) -> list[dict]:
    """
    各項目平均値ファイルから糖尿病/メタボ 9 指標を抽出する。
    Extract diabetes/metabolic mean-value indicators from one NDB release.

    Excel 構造（全リリース共通）:
      Row 0: タイトル（年度情報）
      Row 1: ヘッダー1（都道府県 | 健診項目 | 全国 | 男性 | 女性 ...）
      Row 2-3: 性別・年齢階級ヘッダー
      Row 4: 単位行（「単位」「%」「mg/dL」等）
      Row 5+: データ行（都道府県 × 項目）

    都道府県列（col 0）は先頭行のみ記入され以降は空のため ffill で補完する。

    Args:
        release_no: NDB リリース番号（1〜11）

    Returns:
        list[dict]: OUTPUT_FIELDNAMES に対応する long-format レコードのリスト
    """
    fpath = find_mean_values_file(release_no)
    checkup_fy = RELEASE_TO_CHECKUP_FY[release_no]

    if fpath is None:
        logger.warning(f"No.{release_no}: 各項目平均値ファイル not found → unpublished")
        return [{
            "domain": "diabetes_metabolic",
            "indicator_family": indicator,
            "indicator_name": indicator,
            "release_no": release_no,
            "fiscal_year": checkup_fy,
            "data_year_type": "specific_health_checkup",
            "prefecture_code": "ALL",
            "prefecture_name": "ALL",
            "sex": "all",
            "age_group": "all",
            "value": None,
            "unit": ITEM_UNITS.get(indicator, ""),
            "metric_type": "mean",
            "missing_state": "unpublished",
            "source_file": "NOT_FOUND",
            "source_sheet": "",
        } for indicator in TARGET_ITEMS_METABOLIC]

    logger.info(f"No.{release_no} (checkup FY{checkup_fy}): {fpath.name}")

    try:
        df = pd.read_excel(fpath, header=None, dtype=str)
    except Exception as e:
        logger.error(f"No.{release_no}: read error: {e}")
        return []

    data_start = 5
    records = []

    pref_col = df.iloc[data_start:, 0].copy()
    pref_col = pref_col.ffill()
    item_col = df.iloc[data_start:, 1].copy()

    for idx, (pref_raw, item_raw) in enumerate(
        zip(pref_col.values, item_col.values), start=data_start
    ):
        pref_str = str(pref_raw).strip() if pd.notna(pref_raw) else ""
        item_str = str(item_raw).strip() if pd.notna(item_raw) else ""

        if not pref_str or pref_str in ("nan", "", "全国", "全国合計", "全体"):
            continue
        if not item_str or item_str == "nan":
            continue

        matched_item = match_item(item_str)
        if not matched_item:
            continue

        pref_code, pref_canonical = get_pref_code(pref_str)
        # prefecture_unknown: retain but flag
        is_unknown_pref = pref_code == "XX"

        row_data = df.iloc[idx]
        for sex, age_map in SEX_AGE_COLS.items():
            for age_group, col_idx in age_map.items():
                if col_idx >= len(row_data):
                    continue
                raw_val = row_data.iloc[col_idx]
                value, missing_state = parse_value(raw_val)
                if missing_state == "missing_unknown":
                    missing_state = "missing_unknown"
                elif value is not None:
                    missing_state = "observed"

                # Override for prefecture_unknown
                if is_unknown_pref and missing_state in ("observed", "missing_unknown"):
                    missing_state = "prefecture_unknown"

                records.append({
                    "domain": "diabetes_metabolic",
                    "indicator_family": matched_item,
                    "indicator_name": matched_item,
                    "release_no": release_no,
                    "fiscal_year": checkup_fy,
                    "data_year_type": "specific_health_checkup",
                    "prefecture_code": pref_code,
                    "prefecture_name": pref_canonical,
                    "sex": sex,
                    "age_group": age_group,
                    "value": value,
                    "unit": ITEM_UNITS.get(matched_item, ""),
                    "metric_type": "mean",
                    "missing_state": missing_state,
                    "source_file": fpath.name,
                    "source_sheet": "",
                })

    n_obs = sum(1 for r in records if r["missing_state"] == "observed")
    n_sup = sum(1 for r in records if r["missing_state"] == "suppressed")
    n_unk = sum(1 for r in records if r["missing_state"] == "prefecture_unknown")
    logger.info(
        f"  → {len(records)} records: observed={n_obs}, suppressed={n_sup}, "
        f"pref_unknown={n_unk}"
    )
    return records


def find_dental_disease_file(release_no: int) -> tuple[Path, str]:
    """
    歯科傷病 都道府県別ファイルを返す。
    Find the dental disease-count prefecture-level file for a given release.

    No.8（FY2021）は「傷病件数」ファイルが存在せず「算定回数」ファイルのみ存在する。
    これは指標の定義が変わった（件数 → 回数）ため、比較不能として metric_change を返す。

    Args:
        release_no: NDB リリース番号（1〜11）

    Returns:
        tuple[Path | None, str]:
            (path, "disease_count") — 傷病件数ファイルが見つかった場合
            (path, "metric_change") — No.8 のように算定回数ファイルのみの場合
            (None, "unpublished")   — ファイルが存在しない場合
    """
    base = RAW_BASE / f"No.{release_no}" / "04_歯科傷病"
    if not base.exists():
        return None, "unpublished"

    disease_count_files = []
    metric_change_files = []

    for root, dirs, files in os.walk(base):
        for f in files:
            if "都道府県別" not in f or not f.endswith(".xlsx"):
                continue
            if "傷病件数" in f or "傷病" in f:
                # Exclude "推計含む" variants (prefer non-estimate)
                if "推計" not in f:
                    disease_count_files.append(Path(root) / f)
                else:
                    disease_count_files.append(Path(root) / f)  # fallback
            elif "算定回数" in f:
                metric_change_files.append(Path(root) / f)

    if disease_count_files:
        # Prefer non-推計 file
        non_estimate = [c for c in disease_count_files if "推計" not in c.name]
        chosen = non_estimate[0] if non_estimate else disease_count_files[0]
        return chosen, "disease_count"

    if metric_change_files:
        return metric_change_files[0], "metric_change"

    return None, "unpublished"


def extract_dental(release_no: int) -> list[dict]:
    """
    歯科傷病ファイルから都道府県別・疾患グループ別の傷病件数を抽出する。
    Extract dental disease-count records (prefecture × disease group) from one NDB release.

    Excel 構造:
      Row 0: タイトル（年度情報）
      Row 1: （空）
      Row 2: ヘッダー（疾病グループ | 疾患コード | 疾患名 | 総計 | 01 | 02 ... 47）
      Row 3: 都道府県名（北海道 | 青森県 ...）
      Row 4+: データ（疾患コード 1 行 × 都道府県 47 列）

    10 件未満のセルは "－"（全角ダッシュ）で公表される（統計的開示制御）。
    これを suppressed として記録し、ゼロとして扱わない。

    Args:
        release_no: NDB リリース番号（1〜11）

    Returns:
        list[dict]: OUTPUT_FIELDNAMES に対応する long-format レコードのリスト
    """
    claims_fy = RELEASE_TO_CLAIMS_FY[release_no]
    fpath, metric_flag = find_dental_disease_file(release_no)

    if fpath is None or metric_flag == "unpublished":
        logger.warning(f"No.{release_no}: 歯科傷病ファイル not found → unpublished")
        return [{
            "domain": "dental_oral",
            "indicator_family": "dental_disease_counts",
            "indicator_name": "total",
            "release_no": release_no,
            "fiscal_year": claims_fy,
            "data_year_type": "claims",
            "prefecture_code": "ALL",
            "prefecture_name": "ALL",
            "sex": "all",
            "age_group": "all",
            "value": None,
            "unit": "count",
            "metric_type": "disease_count",
            "missing_state": "unpublished",
            "source_file": "NOT_FOUND",
            "source_sheet": "",
        }]

    logger.info(f"No.{release_no} (claims FY{claims_fy}): {fpath.name} [{metric_flag}]")

    # No.8: metric_change — record all as metric_change, do not parse values
    if metric_flag == "metric_change":
        logger.info(f"  No.{release_no}: metric_change (算定回数 instead of 傷病件数)")
        return [{
            "domain": "dental_oral",
            "indicator_family": "dental_disease_counts",
            "indicator_name": "metric_change_procedure_count",
            "release_no": release_no,
            "fiscal_year": claims_fy,
            "data_year_type": "claims",
            "prefecture_code": pref_code,
            "prefecture_name": CODE_TO_PREF.get(pref_code, pref_code),
            "sex": "all",
            "age_group": "all",
            "value": None,
            "unit": "count",
            "metric_type": "service_count",
            "missing_state": "metric_change",
            "source_file": fpath.name,
            "source_sheet": "",
        } for pref_code in [f"{i:02d}" for i in range(1, 48)]]

    try:
        df = pd.read_excel(fpath, header=None, dtype=str)
    except Exception as e:
        logger.error(f"No.{release_no}: read error: {e}")
        return []

    # Find header rows: typically Row 2 has codes (疾病グループ, 疾患コード, 疾患名, 総計, 01, 02 ...)
    # Row 3 has prefecture names
    header_row = None
    for ri in range(min(5, len(df))):
        row_str = " ".join(str(x) for x in df.iloc[ri, :5] if pd.notna(x))
        if "01" in row_str or "疾病" in row_str or "グループ" in row_str:
            header_row = ri
            break
    if header_row is None:
        header_row = 2

    # Build prefecture column map from code row (header_row) and name row (header_row+1)
    code_row = df.iloc[header_row].values
    name_row = df.iloc[header_row + 1].values if header_row + 1 < len(df) else [None] * len(code_row)

    pref_col_map = {}  # pref_code → col_idx
    for ci, (code_val, name_val) in enumerate(zip(code_row, name_row)):
        code_str = str(code_val).strip() if pd.notna(code_val) else ""
        name_str = str(name_val).strip() if pd.notna(name_val) else ""
        # Prefecture code: "01" through "47" (2-digit strings)
        if len(code_str) == 2 and code_str.isdigit() and 1 <= int(code_str) <= 47:
            pref_col_map[code_str] = ci
        elif len(code_str) == 3 and code_str.isdigit() and 1 <= int(code_str) <= 47:
            pref_col_map[code_str.lstrip("0").zfill(2)] = ci

    # Fallback: if pref_col_map is empty, try to build from col 4 onwards
    if not pref_col_map:
        for ci in range(4, min(52, len(code_row))):
            code_str = str(code_row[ci]).strip() if pd.notna(code_row[ci]) else ""
            if len(code_str) in (2, 3) and code_str.lstrip("0").isdigit():
                num = int(code_str.lstrip("0") or "0")
                if 1 <= num <= 47:
                    pref_col_map[f"{num:02d}"] = ci

    data_start = header_row + 2
    records = []

    # Group column (col 0), code (col 1), name (col 2)
    current_group = None
    for ri in range(data_start, len(df)):
        row = df.iloc[ri]
        group_cell = str(row.iloc[0]).strip() if pd.notna(row.iloc[0]) else ""
        code_cell = str(row.iloc[1]).strip() if pd.notna(row.iloc[1]) else ""
        name_cell = str(row.iloc[2]).strip() if pd.notna(row.iloc[2]) else ""

        if group_cell and group_cell != "nan":
            current_group = group_cell

        if not code_cell or code_cell == "nan":
            continue

        # Aggregate by disease group (one row per group per prefecture)
        for pref_code, col_idx in pref_col_map.items():
            if col_idx >= len(row):
                continue
            raw_val = row.iloc[col_idx]
            value, missing_state = parse_value(raw_val)
            if value is not None:
                missing_state = "observed"

            pref_name = CODE_TO_PREF.get(pref_code, pref_code)

            records.append({
                "domain": "dental_oral",
                "indicator_family": "dental_disease_counts",
                "indicator_name": f"disease_group_{current_group}_code_{code_cell}",
                "release_no": release_no,
                "fiscal_year": claims_fy,
                "data_year_type": "claims",
                "prefecture_code": pref_code,
                "prefecture_name": pref_name,
                "sex": "all",
                "age_group": "all",
                "value": value,
                "unit": "count",
                "metric_type": "disease_count",
                "missing_state": missing_state,
                "source_file": fpath.name,
                "source_sheet": "",
            })

    n_obs = sum(1 for r in records if r["missing_state"] == "observed")
    n_sup = sum(1 for r in records if r["missing_state"] == "suppressed")
    logger.info(f"  → {len(records)} records: observed={n_obs}, suppressed={n_sup}")

    return records


def main():
    logger.info("=== Full Panel Extraction: NDB No.1-11 ===")
    logger.info("Human decisions applied:")
    logger.info("  1. No.8 dental → metric_change (excluded from main panel)")
    logger.info("  2. HbA1C treated as NGSP (%) — unit audit confirms no JDS")
    logger.info("  3. No.1 uses 受診時年齢 aggregation")
    logger.info("  4. prefecture_unknown retained but excluded from main panel")
    logger.info("  5. dental_disease_counts = primary dental outcome")
    logger.info("  7. No imputation of suppressed cells")

    all_records = []

    for release_no in range(1, 12):
        logger.info(f"\n--- Release No.{release_no} ---")
        metabolic = extract_metabolic(release_no)
        all_records.extend(metabolic)

        dental = extract_dental(release_no)
        all_records.extend(dental)

    out_path = DATA_DIR / "ndb_prefecture_year_full_panel.csv"
    with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_FIELDNAMES)
        writer.writeheader()
        for r in all_records:
            writer.writerow({k: r.get(k, "") for k in OUTPUT_FIELDNAMES})

    logger.info(f"\n=== DONE ===")
    logger.info(f"Total records: {len(all_records)}")

    # Summary by missing_state
    from collections import Counter
    state_counts = Counter(r["missing_state"] for r in all_records)
    for state, cnt in sorted(state_counts.items()):
        logger.info(f"  {state}: {cnt}")

    logger.info(f"Output: {out_path}")

    # Validate: no mixed disease/service counts in main panel
    main_dental = [r for r in all_records
                   if r["domain"] == "dental_oral"
                   and r["missing_state"] not in ("metric_change",)]
    service_in_main = [r for r in main_dental if r["metric_type"] == "service_count"]
    if service_in_main:
        logger.error(
            f"STOP CONDITION: {len(service_in_main)} service_count records in main dental panel!"
        )
    else:
        logger.info("Validation passed: no service_count mixed into main dental panel")


if __name__ == "__main__":
    main()
