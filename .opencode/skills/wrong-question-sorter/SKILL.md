---
name: wrong-question-sorter
description: >
  高中錯題分類與詳解：手機拍照/截圖上傳後，按拍辨拆分推五步自動分類，
  再為每題產出步驟化HTML詳解與四層錯題本導覽。
  拍=Google表單收件，辨=Python RapidOCR圖轉文，拆=LLM拆成結構化JSON，
  分=依高中10科章節+錯因五類打標籤並分夾到已分類/未分類，
  推=找類似題+排T+1/T+3/T+7複習+出變式題，
  詳解=每題一份HTML(題目/正解/步驟/防錯)+錯題.html→科目→章節→單題導覽。
  當使用者說「錯題分類」「拍照上傳錯題」「截圖分類」「整理錯題本」
  「分到已分類未分類」「找類似題」「產生詳解」「做詳解HTML」
  「錯題本」「解題解析」時使用此技能。
---

# Wrong Question Sorter（拍辨拆分推）

個人版錯題管線：進已分類/未分類即刪上傳區，不查誰交。

> 本檔案提到的所有路徑（`01_拍_google表單/`、`02_辨_python圖轉文/`、
> `03_拆_結構化/`、`04_分_高中分類/`、`05_推_收集推送/`、`已分類/`、`未分類/`）
> 一律相對於**專案根目錄**（含本 skill 資料夾的上層），不是相對於本檔案。
>
> ⚠️ 但各 `.py` 腳本的命令列相對路徑是**相對於腳本自己的資料夾**解析的。
> 所以從專案根目錄執行時：輸入檔要寫 `../上層資料夾/檔名`，
> 輸出檔只寫檔名（會落在該腳本自己的資料夾）。以下指令都是照此寫的。

## 1. 拍：收件（每人不同，只改設定）

- 每人先照 `01_拍_google表單/Google表單設定步驟.md` 建自己的表單
  （欄位規格見 `01_拍_google表單/表單欄位定義.csv`）
- 然後複製 `01_拍_google表單/config.example.json` 為 `config.json`，
  只改 `form_url` / `form_response_dir` / `subjects` 三項
- `01_拍_google表單/auto_import.py` 會自動讀 `config.json`，
  每 N 秒把該表單回應夾的新圖搬到 `02_辨_python圖轉文/input_images/`
- 辨拆分推的腳本、Prompt、分類體系全部共用，不用每人重寫

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
模型用 `opencode/glm-5.3-flash-free`，見 `opencode.json`）。

離線預切：

```bash
python3 03_拆_結構化/split.py ../02_辨_python圖轉文/output_ocr.json \
  -o 學測截圖_拆解輸出.json
```

欄位：`q_id/stem/stem_fixed/options/student_answer/correct_answer/key_steps/error_point`。
產出檔在 `03_拆_結構化/學測截圖_拆解輸出.json`。

## 4. 分：分類+分夾

體系見 `04_分_高中分類/高中各科章節分類體系.json`（10科+錯因五類：
概念不清/審題疏漏/計算失誤/記憶混淆/解題策略錯）。
Prompt 見 `04_分_高中分類/分類Prompt_muse-spark.md`。

```bash
python3 04_分_高中分類/classify.py ../03_拆_結構化/學測截圖_拆解輸出.json \
  -o 學測截圖_分類輸出.json
python3 04_分_高中分類/organize.py
```

產出檔在 `04_分_高中分類/學測截圖_分類輸出.json`。

`organize.py` 規則：confidence>=0.55 且字數>=10 進 `已分類/<科目>/<單元>/`，
否則進 `未分類/`；個人版進夾即刪上傳區三夾
（input_images + File responses + 收件匣）。總表見 `分類結果總表.csv`。

## 5. 推：類似題+複習

```bash
python3 05_推_收集推送/push_similar.py \
  --new ../04_分_高中分類/學測截圖_分類輸出.json \
  --db 錯題庫範例.csv
```

純標準庫字元 bigram 餘弦，同科目+0.15、同知識點+0.25。
變式題 Prompt 見 `05_推_收集推送/變式題Prompt_muse-spark.md`。

## 6. 詳解 HTML：每題一份詳解，放進對應章節資料夾

把 `已分類/<科目>/<單元>/` 裡的每張錯題圖做成一份單檔 HTML 詳解，
與原圖同目錄、同名（`.html`），另在每個章節資料夾產生 `index.html` 索引。

1. 先用 OCR 取得題目文字（比對用，題目以圖片為準）：
   `02_辨_python圖轉文/ocr_vision.py` 只掃單一目錄，要遞迴已分類時
   直接呼叫它的 `process_one()` 逐檔跑。
2. **由 LLM 看圖解題**（不要只靠關鍵字分類器）：讀原圖 → 校正 OCR 錯字 →
   解出正解 → 寫步驟化詳解 → 寫具體防錯提醒。計算題必須用 `python3` 驗算。
3. 每題寫一筆 JSON 到 `05_推_收集推送/詳解內容/batch_*.json`，
   欄位規格見 `05_推_收集推送/詳解HTML產生器.py` 開頭的說明。
4. 產生 HTML（四層導覽一次重建）：

```bash
python3 05_推_收集推送/錯題本產生器.py
```

產生四層可逐層點進去的頁面：

| 層 | 檔案 | 內容 |
|---|---|---|
| 1 | `錯題.html`（根目錄） | 總表：科目→章節→題目全列，每題直接連到詳解 |
| 2 | `已分類/<科目>/<科目>.html` | 科目頁：各章節卡片＋題目清單 |
| 3 | `已分類/<科目>/<單元>/<科目><單元>.html` | 章節頁：該章節全部題目的完整詳解，可整章列印 |
| 4 | `已分類/<科目>/<單元>/<圖檔名>.html` | 單題詳解頁：含原題圖（base64 內嵌） |

另有 `已分類/<科目>/<單元>/index.html` 章節索引。
所有頁面都有麵包屑與「回到上一層」連結，`python3 05_推_收集推送/詳解HTML產生器.py`
可單獨重建第 4 層。

圖片 base64 內嵌（單檔可分享、可離線開啟），
依 `right_options`/`wrong_options` 標綠正解刪除錯誤選項。

數學式子用 Unicode 純文字（a²、√3、≤、π），不要寫 LaTeX。
一圖多題時在 JSON 加 `"html_name": "<原檔名>-1.html"` 等避免檔名衝突。

## 封存（可選）

```bash
python3 01_拍_google表單/archive_input_images.py --run
```

只清 input_images 暫存，不動 File responses 原檔（除非已跑過 organize 個人版）。
