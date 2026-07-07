"""
プロトタイプ long-format データ抽出スクリプト
Builds: data/processed/ndb_prefecture_year_prototype.csv

Rules:
  - Read raw files ONLY; never write to raw/
  - Distinguish missing states: suppressed / unpublished / not_applicable / missing_unknown / parse_error
  - Do not invent data
  - Do not impute suppressed cells

Extracts:
  - Domain 1: Diabetes/metabolic — HbA1C & 空腹時血糖 mean values by prefecture × sex × age group
    Sources: 各項目の平均値 files from No.1 (FY2013), No.6 (FY2018), No.11 (FY2023)
  - Domain 2: Dental/oral — 歯科傷病 都道府県別 counts
    Sources: 都道府県別傷病件数 from No.1 (FY2014), No.6 (FY2019), No.11 (FY2024)
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

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(PROJECT_DIR / "data" / "processed" / "extraction.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

# 都道府県コードマップ（JIS X 0401）
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

# リリース番号 → 特定健診年度マップ
RELEASE_TO_CHECKUP_FY = {
    1: 2013, 2: 2014, 3: 2015, 4: 2016, 5: 2017,
    6: 2018, 7: 2019, 8: 2020, 9: 2021, 10: 2022, 11: 2023,
}
# リリース番号 → レセプト年度マップ
RELEASE_TO_CLAIMS_FY = {
    1: 2014, 2: 2015, 3: 2016, 4: 2017, 5: 2018,
    6: 2019, 7: 2020, 8: 2021, 9: 2022, 10: 2023, 11: 2024,
}

# 対象アイテム（各項目平均値ファイルでの表記パターン）
TARGET_ITEMS_METABOLIC = {
    "HbA1C": ["HbA1C", "HbA1c"],
    "fasting_glucose": ["空腹時血糖"],
    "BMI": ["BMI"],
    "waist_circumference": ["腹囲"],
    "systolic_BP": ["収縮期血圧"],
}

AGE_GROUPS = ["40-44", "45-49", "50-54", "55-59", "60-64", "65-69", "70-74", "total"]

SUPPRESSION_MARKERS = {"-", "－", "−", "*", "***", "x", "X", "　", "▲"}


def parse_value(val):
    """値のパース。suppression/missing状態を判別して返す"""
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return None, "missing_unknown"
    s = str(val).strip()
    if s in SUPPRESSION_MARKERS or s == "":
        return None, "suppressed"
    if s in ("-", "－", "−"):
        return None, "suppressed"
    try:
        return float(s.replace(",", "").replace("，", "")), None
    except (ValueError, TypeError):
        return None, "parse_error"


def find_mean_values_file(release_no: int) -> Path:
    """各項目の平均値 都道府県別ファイルのパスを返す"""
    base = RAW_BASE / f"No.{release_no}" / "07_特定健診 検査"
    candidates = []
    for root, dirs, files in os.walk(base):
        for f in files:
            if "各項目の平均値" in f and "都道府県別" in f and f.endswith(".xlsx"):
                candidates.append(Path(root) / f)
    # ※1 ファイル（公費なし）を優先
    for c in candidates:
        if "※1" in str(c) or "01_公費レセプトを含まないデータ" in str(c):
            return c
    return candidates[0] if candidates else None


def extract_metabolic_from_mean_file(release_no: int) -> list:
    """
    各項目平均値ファイルから糖尿病/メタボ指標を抽出。
    構造:
      Row 0: タイトル
      Row 1: ヘッダー1（都道府県名 | 項目名 | 男性 各年齢 | 合計 | 女性 各年齢 | 合計）
      Row 2: ヘッダー2（男性・女性の区別）
      Row 3: ヘッダー3（年齢階級）
      Row 4: ヘッダー4（単位）
      Row 5+: データ（都道府県 × 項目）
    """
    fpath = find_mean_values_file(release_no)
    if fpath is None:
        logger.warning(f"No.{release_no}: 各項目平均値ファイルが見つかりません")
        return []

    checkup_fy = RELEASE_TO_CHECKUP_FY[release_no]
    logger.info(f"No.{release_no} (FY{checkup_fy}): {fpath.name} を読み込み中...")

    try:
        df = pd.read_excel(fpath, header=None, dtype=str)
    except Exception as e:
        logger.error(f"No.{release_no}: 読み込みエラー: {e}")
        return [{"candidate_family": "diabetes_metabolic",
                 "item_name": "parse_error",
                 "year": checkup_fy,
                 "prefecture_code": "XX",
                 "prefecture_name": "parse_error",
                 "sex": "unknown",
                 "age_group": "unknown",
                 "value": None,
                 "missing_state": "parse_error",
                 "source_release_no": release_no,
                 "source_file": fpath.name}]

    # ヘッダー行数の確認（Row 3 に年齢情報 Row 4 に単位）
    # データは Row 5 から
    data_start = 5
    records = []

    # 都道府県名を前方補完
    pref_col = df.iloc[data_start:, 0].copy()
    pref_col = pref_col.ffill()
    item_col = df.iloc[data_start:, 1].copy()

    # 列インデックス: 男性 cols 2-9 (40-44, 45-49, ..., 70-74, 合計), 女性 cols 10-17
    # col 2: 男 40-44, col 3: 男 45-49, ..., col 8: 男 70-74, col 9: 男 合計
    # col 10: 女 40-44, ..., col 16: 女 70-74, col 17: 女 合計
    sex_age_cols = {
        "male": {
            "40-44": 2, "45-49": 3, "50-54": 4, "55-59": 5,
            "60-64": 6, "65-69": 7, "70-74": 8, "total": 9,
        },
        "female": {
            "40-44": 10, "45-49": 11, "50-54": 12, "55-59": 13,
            "60-64": 14, "65-69": 15, "70-74": 16, "total": 17,
        },
    }

    for i, (pref_raw, item_raw) in enumerate(
        zip(pref_col.values, item_col.values), start=data_start
    ):
        pref_name = str(pref_raw).strip() if pd.notna(pref_raw) else None
        item_raw_str = str(item_raw).strip() if pd.notna(item_raw) else None

        if not pref_name or pref_name in ("nan", "", "全国", "全国合計"):
            continue
        if not item_raw_str or item_raw_str == "nan":
            continue

        # 項目名マッチング
        matched_item = None
        for canonical, patterns in TARGET_ITEMS_METABOLIC.items():
            for pat in patterns:
                if pat in item_raw_str:
                    matched_item = canonical
                    break
            if matched_item:
                break
        if not matched_item:
            continue

        # 都道府県コード
        pref_code = PREFECTURE_CODE_MAP.get(pref_name, "XX")
        if pref_code == "XX":
            # 部分一致を試みる
            for k, v in PREFECTURE_CODE_MAP.items():
                if k in pref_name or pref_name in k:
                    pref_code = v
                    pref_name = k
                    break

        # 各セックス・年齢グループの値を抽出
        row_data = df.iloc[i]
        for sex, age_map in sex_age_cols.items():
            for age_group, col_idx in age_map.items():
                if col_idx >= len(row_data):
                    continue
                raw_val = row_data.iloc[col_idx]
                value, missing_state = parse_value(raw_val)
                records.append({
                    "candidate_family": "diabetes_metabolic",
                    "item_name": matched_item,
                    "year": checkup_fy,
                    "prefecture_code": pref_code,
                    "prefecture_name": pref_name,
                    "sex": sex,
                    "age_group": age_group,
                    "value": value,
                    "missing_state": missing_state if missing_state else "observed",
                    "source_release_no": release_no,
                    "source_file": fpath.name,
                })

    logger.info(f"  → {len(records)} レコードを抽出 ({len(set(r['prefecture_name'] for r in records))} 都道府県)")
    return records


def find_dental_disease_prefecture_file(release_no: int) -> Path:
    """歯科傷病 都道府県別ファイルのパスを返す"""
    base = RAW_BASE / f"No.{release_no}" / "04_歯科傷病"
    for root, dirs, files in os.walk(base):
        for f in files:
            if "都道府県別" in f and f.endswith(".xlsx"):
                return Path(root) / f
    return None


def extract_dental_from_disease_file(release_no: int) -> list:
    """
    歯科傷病 都道府県別ファイルから上位疾患データを抽出。
    構造:
      Row 0: タイトル（FY情報）
      Row 1: (空)
      Row 2: ヘッダー1（疾病グループ | 疾患コード | 疾患名 | 総計 | 01北海道 | 02青森 ...）
      Row 3: ヘッダー2（NaN | NaN | NaN | NaN | 北海道 | 青森 ...）
      Row 4+: データ（疾病コード × 都道府県）
    """
    fpath = find_dental_disease_prefecture_file(release_no)
    if fpath is None:
        logger.warning(f"No.{release_no}: 歯科傷病 都道府県別ファイルが見つかりません")
        return []

    claims_fy = RELEASE_TO_CLAIMS_FY[release_no]
    logger.info(f"No.{release_no} (レセプトFY{claims_fy}): {fpath.name} を読み込み中...")

    try:
        df = pd.read_excel(fpath, header=None, dtype=str)
    except Exception as e:
        logger.error(f"No.{release_no}: 読み込みエラー: {e}")
        return []

    # ヘッダー位置を特定（"疾病グループ" または "疾患名" が含まれる行）
    header_row = 2  # デフォルト
    for ri in range(min(5, len(df))):
        row_str = " ".join(str(x) for x in df.iloc[ri, :] if pd.notna(x))
        if "疾病" in row_str or "傷病" in row_str or "グループ" in row_str:
            header_row = ri
            break

    # 都道府県名は Row header_row+1（行3）にある
    pref_name_row = df.iloc[header_row + 1].values
    # 総計は col 3、都道府県は col 4以降
    data_start_row = header_row + 2
    pref_cols = {}  # col_idx → pref_name
    for ci, pref_raw in enumerate(pref_name_row[4:], start=4):
        pref_str = str(pref_raw).strip() if pd.notna(pref_raw) else ""
        if pref_str and pref_str not in ("nan", "", "合計", "総計"):
            pref_cols[ci] = pref_str

    if not pref_cols:
        logger.warning(f"No.{release_no}: 都道府県列が見つかりません")
        return []

    # 対象疾患: う歯（龋歯）、歯周病
    TARGET_DENTAL_KEYWORDS = {
        "caries": ["う歯", "う蝕", "齲歯", "龋"],
        "periodontal": ["歯周", "歯肉", "歯槽"],
        "dental_total": ["歯科", "口腔", "口内", "歯"],
    }

    records = []
    for ri in range(data_start_row, len(df)):
        row = df.iloc[ri]
        disease_name = str(row.iloc[2]).strip() if pd.notna(row.iloc[2]) else ""
        if not disease_name or disease_name == "nan":
            continue

        # 疾患マッチング（最初にマッチした1種類のみ）
        matched_domain = None
        for domain, keywords in TARGET_DENTAL_KEYWORDS.items():
            if any(kw in disease_name for kw in keywords):
                matched_domain = domain
                break
        if not matched_domain:
            continue

        disease_code = str(row.iloc[1]).strip() if pd.notna(row.iloc[1]) else "unknown"

        for col_idx, pref_name in pref_cols.items():
            raw_val = row.iloc[col_idx] if col_idx < len(row) else None
            value, missing_state = parse_value(raw_val)
            pref_code = PREFECTURE_CODE_MAP.get(pref_name, "XX")
            if pref_code == "XX":
                for k, v in PREFECTURE_CODE_MAP.items():
                    if k in pref_name or pref_name in k:
                        pref_code = v
                        pref_name = k
                        break

            records.append({
                "candidate_family": "dental_oral",
                "item_name": f"dental_disease_{matched_domain}",
                "year": claims_fy,
                "prefecture_code": pref_code,
                "prefecture_name": pref_name,
                "sex": "all",
                "age_group": "all",
                "value": value,
                "missing_state": missing_state if missing_state else "observed",
                "source_release_no": release_no,
                "source_file": fpath.name,
            })

    logger.info(f"  → {len(records)} レコードを抽出 ({len(set(r['prefecture_name'] for r in records))} 都道府県)")
    return records


def build_prototype_data():
    """プロトタイプ long-format データを構築"""
    logger.info("=== プロトタイプデータ抽出開始 ===")
    all_records = []

    # Domain 1: Diabetes/metabolic — No.1, No.6, No.11
    for rel_no in [1, 6, 11]:
        records = extract_metabolic_from_mean_file(rel_no)
        all_records.extend(records)

    # Domain 2: Dental — No.1, No.6, No.11
    for rel_no in [1, 6, 11]:
        records = extract_dental_from_disease_file(rel_no)
        all_records.extend(records)

    # CSV 書き出し
    out_path = DATA_DIR / "ndb_prefecture_year_prototype.csv"
    fieldnames = [
        "candidate_family", "item_name", "year",
        "prefecture_code", "prefecture_name",
        "sex", "age_group",
        "value", "missing_state",
        "source_release_no", "source_file",
    ]
    with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_records)

    logger.info(f"プロトタイプデータ書き出し完了: {out_path} ({len(all_records)} 行)")

    # サマリー統計
    from collections import Counter
    missing_counts = Counter(r["missing_state"] for r in all_records)
    family_counts = Counter(r["candidate_family"] for r in all_records)
    year_counts = Counter(r["year"] for r in all_records)

    logger.info("=== プロトタイプデータ サマリー ===")
    logger.info(f"総レコード数: {len(all_records)}")
    logger.info(f"候補ファミリー内訳: {dict(family_counts)}")
    logger.info(f"年度内訳: {dict(sorted(year_counts.items()))}")
    logger.info(f"欠損状態内訳: {dict(missing_counts)}")
    observed = sum(1 for r in all_records if r["missing_state"] == "observed")
    suppressed = sum(1 for r in all_records if r["missing_state"] == "suppressed")
    logger.info(f"観測値: {observed} ({100*observed/max(1,len(all_records)):.1f}%)")
    logger.info(f"抑制値: {suppressed} ({100*suppressed/max(1,len(all_records)):.1f}%)")

    return all_records


if __name__ == "__main__":
    records = build_prototype_data()
    logger.info("=== 完了 ===")
