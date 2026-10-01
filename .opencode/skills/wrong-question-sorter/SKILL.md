---
name: wrong-question-sorter
description: >
  高中錯題自動分類：手機拍照/截圖上傳後，按拍辨拆分推五步自動分類。
  拍=Google表單收件，辨=Python RapidOCR圖轉文，拆=LLM拆成結構化JSON，
  分=依高中10科章節+錯因五類打標籤並分夾到已分類/未分類，
  推=找類似題+排T+1/T+3/T+7複習+出變式題。
  當使用者說「錯題分類」「拍照上傳錯題」「截圖分類」「整理錯題本」
  「分到已分類未分類」「找類似題」時使用此技能。
---

# Wrong Question Sorter（拍辨拆分推）

個人版錯題管線：進已分類/未分類即刪上傳區，不查誰交。

## 1. 拍：收件

- Google表單規格見 `01_拍_google表單/表單欄位定義.csv`，設定步驟見
  `01_拍_google表單/Google表單設定步驟.md`
- 表單回應檔會同步到 `錯題拍照上傳_學號 (File responses)/錯題照片 (File responses)/`
- `01_拍_google表單/auto_import.py` 的 `SOURCE_DIR` 已指向該夾，
  跑它即每30秒自動搬新圖到 `02_辨_python圖轉文/input_images/`

## 2. 辨：圖轉文

```bash
pip install -r 02_辨_python圖轉文/requirements.txt
python3 02_辨_python圖轉文/ocr_vision.py
```

產出 `02_辨_python圖轉文/output_ocr.json`（含 confidence / need_retake）。
長條英文截圖若 confidence=0，先照 `02_辨_python圖轉文/使用說明.md`
重截大一點 Refuge，或直接把圖貼給 LLM 用視覺補救後再往下走。

## 3. 拆：結構化

Prompt 見 `03_拆_結構化/拆解Prompt_muse-spark.md`（貼進 opencode，
模型用 `opencode/muse-spark-1.3-contributor-free`，見 `opencode.json`）。

離線預切：

```bash
python3 03_拆_結構化/split.py 02_辨_python圖轉文/output_ocr.json \
  -o 03_拆_結構化/學測截圖_拆解輸出.json
```

欄位：`q_id/stem/stem_fixed/options/student_answer/correct_answer/key_steps/error_point`。

## 4. 分：分類+分夾

體系見 `04_分_高中分類/高中各科章節分類體系.json`（10科+錯因五類：
概念不清/審題疏漏/計算失誤/記憶混淆/解題策略錯）。
Prompt 見 `04_分_高中分類/分類Prompt_muse-spark.md`。

```bash
python3 04_分_高中分類/classify.py 03_拆_結構化/學測截圖_拆解輸出.json \
  -o 04_分_高中分類/學測截圖_分類輸出.json
python3 04_分_高中分類/organize.py
```

`organize.py` 規則：confidence>=0.55 且字數>=10 進 `已分類/<科目>/<單元>/`，
否則進 `未分類/`；個人版進夾即刪上傳區三夾
（input_images + File responses + 收件匣）。總表見 `分類結果總表.csv`。

## 5. 推：類似題+複習

```bash
python3 05_推_收集推送/push_similar.py \
  --new 04_分_高中分類/學測截圖_分類輸出.json \
  --db 05_推_收集推送/錯題庫範例.csv
```

純標準庫字元 bigram 餘弦，同科目+0.15、同知識點+0.25。
變式題 Prompt 見 `05_推_收集推送/變式題Prompt_muse-spark.md`。

## 封存（可選）

```bash
python3 01_拍_google表單/archive_input_images.py --run
```

只清 input_images 暫存，不動 File responses 原檔（除非已跑過 organize 個人版）。
