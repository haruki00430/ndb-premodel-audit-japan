# IJMI 投稿チェックリスト

**論文**: A Pre-Model Audit of Administrative Healthcare Data for AI-Oriented Research: Evidence from NDB Open Data releases No.1–No.11  
**投稿先**: International Journal of Medical Informatics (Elsevier; ISSN 1386-5056)  
**論文種別**: Original Research Article  
**投稿システム**: [Editorial Manager — IJMI](https://www.editorialmanager.com/ijmi/default.aspx)  
**パッケージ**: `submission_package_IJMI/`

## 前誌投稿経緯

| 項目 | 内容 |
|------|------|
| 前投稿先 | Journal of Biomedical Informatics（JBI-26-2457） |
| 判定 | Desk rejection（査読なし、2026-07-08） |
| 理由 | JBI 2022年以降の ML 手法論重点ポリシーに合致しない |

---

## 1. IJMI 規定 vs 本稿（2026-07-09 時点）

| 項目 | IJMI 規定 | 本稿 | 判定 |
|------|-----------|------|------|
| Abstract | ≤300語 | 204語（構造化） | ✅ |
| 本文 | ≤3,000語（表・図除く） | 約2,977語 | ✅ |
| 本文中の表 | 最大3 | Table 1–3 | ✅ |
| 図 | 最大4 | Figure 1 | ✅ |
| Summary Table | 2–4 bullet points | 4項目（別ファイル） | ✅ |
| Highlights | 3–5項目、各≤85文字 | 5項目 | ✅ |
| Graphical abstract | 推奨（531×1328 px） | 1328×531 px | ✅ |
| 補足表 | 上限なし（別アップロード） | S1–S3 統合版 | ✅ |
| ML checklist | AI/ML手法論のみ必須 | データ監査論文（不要） | ✅ |
| 査読 | 単一匿名 | 著者名入り原稿 | ✅ |

---

## 2. 投稿ファイル一覧

| ファイル | 用途 | アップロード |
|---------|------|-------------|
| `IJMI_Paper1_Manuscript_IJMI_Submission.docx` | 論文本体 | ✅ |
| `IJMI_Paper1_Cover_Letter.docx` | カバーレター | ✅ |
| `IJMI_Paper1_Highlights.docx` | Highlights | ✅ |
| `IJMI_Paper1_Summary_Table.docx` | Summary Table | ✅ |
| `IJMI_Paper1_Graphical_Abstract.png` | Graphical abstract | ✅ |
| `IJMI_Paper1_Figure1.png` | Figure 1（個別） | ✅ |
| `IJMI_Paper1_Supplementary_Tables.docx` | Supplementary Tables S1–S3 | ✅ |
| `IJMI_Paper1_Declaration_of_Competing_Interests.docx` | 利益相反 | ✅（または EM 上で入力） |
| `Guide for authors ...pdf` | 参照用 | ❌ 投稿不要 |
| `*_backup_*.docx` | バックアップ | ❌ 投稿不要 |
| `IJMI_Paper1_Supplementary_Table_S1.docx` | 旧版（S1のみ） | ❌ 統合版を使用 |

---

## 3. 公開リポジトリ・Zenodo

| 項目 | URL / ID | 状態 |
|------|----------|------|
| GitHub | https://github.com/haruki00430/ndb-premodel-audit-japan | README・CITATION.cff を IJMI に更新済 |
| Zenodo | https://doi.org/10.5281/zenodo.21230851 (v1.0.0) | コード・データ公開済（再アップロード不要） |

原稿の Code availability 記載と一致することを投稿前に確認する。

---

## 4. 投稿前チェックリスト

### 原稿・付属書類

- [x] `Statement of significance.` プレースホルダを削除
- [x] 構造変化件数を9件に統一（Cover Letter / Highlights / Summary / Results 4.6）
- [x] 本文表3つ・補足表 S1–S3 に整理
- [x] カバーレター日付を 2026-07-09 に更新
- [ ] 著者全員の最終承認を確認
- [ ] 原稿を Word で開き、表・図のレイアウトを目視確認

### Editorial Manager

- [ ] アカウント作成・ログイン
- [ ] Article type: **Original Research Article**
- [ ] 上記ファイルをアップロード（バックアップ・旧S1は除外）
- [ ] Declarations（Funding / COI / Ethics / AI use）をシステムにも入力
- [ ] Corresponding author の連絡先（メール・電話・所属）を入力
- [ ] Keywords を入力（原稿と一致）
- [ ] JBI 投稿歴を Cover Letter どおり開示

### GitHub（推奨・投稿当日）

- [ ] `README.md` / `CITATION.cff` の変更を commit & push

---

*作成: 2026-07-09*
