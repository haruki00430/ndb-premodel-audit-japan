# Assumptions to Confirm

**Project**: Paper 1 — NDB Open Data AI-Readiness Assessment
**Created**: 2026-07-06
**Purpose**: Items requiring human confirmation before proceeding to full extraction

---

| # | question | why_it_matters | proposed_handling | confirmation_needed_from_human |
|---|----------|----------------|-------------------|-------------------------------|
| 1 | Should No.8 dental disease data (「算定回数」) be treated as comparable to No.1–7, 9 (「傷病件数」)? | 傷病件数（disease cases）と算定回数（procedure counts）は概念が異なる。No.8のみ指標が異なるため、時系列比較に影響する。 | No.8をfeasibility table上でformat_change注記し、歯科傷病の時系列パネルからNo.8を除外する | Human must decide: exclude No.8 from dental disease panel OR flag as "metric_change" in missing_state |
| 2 | 特定健診質問票はNo.1（FY2013特定健診）で存在しない。質問票指標の解析開始年度はNo.2（FY2014）とするか？ | No.1に質問票データがないため、喫煙・飲酒・運動習慣等の解析パネルは10年分（FY2014–2023）となる | No.1の質問票セルを「unpublished」として記録し、解析はFY2014開始とする | Confirm: start questionnaire panel from FY2014 (10 years), not FY2013 (11 years) |
| 3 | 「各項目の平均値」ファイルで「都道府県情報不明」（prefecture_code = XX）のエントリをどう扱うか？ | No.6, No.11 などで1行「都道府県情報不明」が含まれる。これは地理コード不明のレコードを集計したものと推定される | 都道府県パネルの解析では除外し、「not_applicable」として記録する | Confirm: exclude prefecture_unknown rows from prefecture-year panel |
| 4 | HbA1CはNo.1–2では「NGSP値」表記、No.3以降は単純「HbA1c」。単位の定義は変わっているか？ | NGSPとJDSでは換算式が異なるが、No.3以降もNGSP基準に移行済みと推定。ただし確認が必要。 | 同一単位（NGSP%）として扱う。タイトル行に「NGSP値」の記載がある場合はmetadataに記録する | Human should verify: confirm all releases use NGSP% for HbA1C (not JDS%) |
| 5 | No.1 特定健診検査データは「受診時年齢での集計」と「年度末年齢での集計」の2フォルダが存在する。どちらを使用するか？ | No.2以降はこの区別がなく（受診時年齢のみ）、No.1でのみ選択肢がある。年齢集計基準の一貫性に影響する。 | No.2以降との一貫性のため「受診時年齢での集計」を使用する | Confirm: use 受診時年齢 collection for No.1 to maintain consistency with No.2+ |
| 6 | 処方薬（05_処方薬）の都道府県別データには糖尿病治療薬（ビグアナイド系、インスリン等）が識別可能なコードが含まれているか？ | Paper 1の候補指標として糖尿病処方薬割合を含めるには、薬効分類コードでの絞り込みが必要 | NDB処方薬ファイルの薬効コード体系を別途確認する。NDB ffillバグ（薬効分類コードは先頭行のみ）に注意。 | Human needs to check: confirm diabetes drug codes (e.g., 396薬効コード) are available in prescription files |
| 7 | 歯科指標として「歯科診療行為（算定回数）」の都道府県別ファイルは何を表すか？「歯科傷病」との違いは？ | 診療行為 = 実施された処置の回数。傷病 = 診断された疾病件数。どちらがOutcome指標として適切かが不明。 | Paper 1の研究設計に合わせて決定が必要。傷病件数のほうがOutcomeとして解釈しやすいが、診療行為のほうが時系列データが充実（10/11 releases）。 | Human must decide: which dental indicator to use as primary outcome — 傷病件数 or 診療行為算定回数 |
| 8 | random_glucose（随時血糖）は6/11 releases（Grade C）。これを補完的指標として含めるか？ | 空腹時血糖（11/11）との比較に使えるが、6リリースのみでは時系列パネルとして限定的。 | Grade Cとして文書化のみ。Supplementに掲載する場合はfeasibility noteが必要。 | Confirm: random glucose is documentation-only; primary glucose indicator is fasting glucose |

---

## Additional Notes

- **抑制値（suppressed）の取り扱い**: プロトタイプデータの21.3%が抑制値。これは歯科傷病データに集中しており、糖尿病/メタボ指標（平均値）には抑制なし。感度分析でimputation手法を検討する場合は別途指示が必要。

- **二次医療圏データの活用**: No.6以降、特定健診データが二次医療圏別にも提供されている。Paper 1のRQ（都道府県パネル）には不要だが、空間統計解析（Paper 2以降）の基盤として重要。

- **NDB No.1の年齢カバレッジ**: No.1は40–74歳のみ。No.10–11では75歳以上のデータも追加された可能性がある。年齢カバレッジの変化を確認する。
