# 錯題分類與詳解系統 - 總覽（拍辨拆分推＋詳解）

> 適用：高中專題 / Agent應用課，LLM 統一用 opencode 內建模型
> （本 repo 釘 `opencode/glm-5.3-flash-free`；原 `muse-spark-1.3` 已下架）

## 流程總圖

```
[01拍]手機拍照/截圖
  → Google表單上傳 (學號/科目/照片)
  → Drive收件匣 + Sheets錯題庫(原始列)
  → [02辨]Python ocr_vision.py 圖轉文 (RapidOCR)
  → output_ocr.json
  → [03拆]LLM 拆解成結構化JSON (一題一切，含正解與key_steps)
  → 學測截圖_拆解輸出.json
  → [04分]LLM 依高中章節+錯因分類
  → 學測截圖_分類輸出.json + organize.py 分夾
  → [05推]push_similar.py 收集+找類似題+排複習+出變式題
  → 個人錯題本 + LINE/Email推送
  → [詳解]錯題本產生器：每題一份HTML詳解 + 四層導覽
  → 錯題.html → 科目.html → 章節.html → 單題詳解.html
```

## 各步對應資料夾

| 步 | 資料夾 | 關鍵產出 | LLM |
|---|---|---|---|
| 0 | 00_系統架構 | 本檔 + opencode.json + AGENTS.md | opencode 內建 |
| 1 拍 | 01_拍_google表單 | 表單規格 + Apps Script + config.json | - |
| 2 辨 | 02_辨_python圖轉文 | ocr_vision.py + output_ocr.json | - (本機OCR) |
| 3 拆 | 03_拆_結構化 | Prompt + split.py + 拆解輸出.json | opencode 內建 |
| 4 分 | 04_分_高中分類 | 章節體系.json + classify.py + organize.py | opencode 內建 |
| 5 推 | 05_推_收集推送 | 錯題庫.csv + push_similar.py + 變式題Prompt | opencode 內建 |
| 6 詳解 | 05_推_收集推送 | 詳解HTML產生器.py + 錯題本產生器.py | opencode 內建 |

## 快速跑通 (老師Demo用，5分鐘)

```bash
cd 02_辨_python圖轉文
pip install -r requirements.txt
python3 ocr_vision.py

cd ../03_拆_結構化
python3 split.py ../02_辨_python圖轉文/output_ocr.json -o 範例_拆解輸出.json

cd ../04_分_高中分類
python3 classify.py ../03_拆_結構化/範例_拆解輸出.json -o 範例_分類輸出.json

cd ../05_推_收集推送
python3 push_similar.py --new ../04_分_高中分類/範例_分類輸出.json --db 錯題庫範例.csv
```

全程不需 API Key 即可跑通；要更高準確率才把 OCR 文字貼給 opencode，
用各資料夾內的 Prompt 精修一次（03 拆 / 04 分 / 05 推）。

> ⚠️ 各 `.py` 腳本的命令列相對路徑是**相對於腳本自己的資料夾**解析的。
> 從專案根目錄執行時，輸入檔要寫 `../上層資料夾/檔名`，輸出檔只寫檔名。

## 詳解 HTML 與錯題本導覽

把每道錯題做成一份單檔 HTML 詳解（圖片 base64 內嵌，可離線開啟、可直接傳給學生），
並產生四層可逐層點進去的導覽：

| 層 | 檔案 | 內容 |
|---|---|---|
| 1 | `錯題.html`（根目錄） | 總表：科目→章節→題目，每題直接連詳解 |
| 2 | `已分類/<科目>/<科目>.html` | 科目頁：各章節卡片＋題目清單 |
| 3 | `已分類/<科目>/<單元>/<科目><單元>.html` | 章節頁：整章題目完整詳解，可整章列印 |
| 4 | `已分類/<科目>/<單元>/<圖檔名>.html` | 單題詳解頁：含原題圖 |

另有 `已分類/<科目>/<單元>/index.html` 章節索引。
所有頁面都有麵包屑與「回到上一層」連結。

```bash
# 1) 先讓 LLM 看圖解題，輸出內容 JSON 到 05_推_收集推送/詳解內容/
#    欄位規格見 05_推_收集推送/詳解HTML產生器.py 開頭說明
# 2) 一次重建全部四層
python3 05_推_收集推送/錯題本產生器.py
```

詳解內容含：題目（正解綠底、錯誤選項刪除線）、學生作答、正解、
步驟化詳解、具體防錯提醒、複習排程（T+1/T+3/T+7）。
數學式子用 Unicode 純文字（a²、√3、≤、π），不寫 LaTeX。

---

## 輕量版 Agent（舊版，單機快速用）

手機拍照 / 截圖 → 自動分類 → 弱點追蹤。OpenCode Skill，可單獨用，也可掛到學習教練 Agent。

## 快速開始

```bash
pip install -r requirements.txt
export MODEL_API_KEY=你的Key   # 或 OPENAI_API_KEY=sk-...
export MODEL=gpt-4o-mini       # 或任何支援 JSON 輸出的模型
python agent.py
```

無 Key 演示（離線 mock）：

```bash
python3 -c "import tools; print(tools.llm_classify('牛頓第二定律 F=ma'))"
python3 -c "import tools; print(tools.add_mistake_from_text('log(a^2)比較',''))"
python3 -c "import tools; print(tools.get_mistake_stats())"
```

## 五步流程

拍 → 辨 → 拆 → 分 → 推，詳見 `.opencode/skills/wrong-question-sorter/SKILL.md`。

## 網頁上傳

```bash
python3 -m streamlit run app.py
```

手機拍照（單張）／截圖多選批量分類／錯題本回看。手機用同一 Wi-Fi 的 Network URL。

## 目錄

- `.opencode/skills/wrong-question-sorter/SKILL.md` — skill 定義（給 Agent 讀）
- `AGENTS.md` — 專案硬規則（流程固定、03 只出 JSON、04 只能選體系內的詞、05 一次 3 題）
- `opencode.json` — 模型與指令設定（`instructions` 指向 AGENTS.md）
- `SKILL.md` — 輕量版 skill 定義（給 Agent 讀）
- `tools.py` — Function Calling 實作
- `agent.py` — Agent 迴圈範例
- `app.py` — Streamlit 上傳＋錯題本
- `user_memory.example.json` — 資料格式範本
- `mistakes_images/` — 圖片區（照片不進版控）
- `05_推_收集推送/詳解內容/` — 詳解內容 JSON（產生器的輸入）

## 隱私

`mistakes_images/*`、`*user_memory.json`、`*.pdf`、產生的詳解 HTML（`*.html`）皆已 gitignore，
公開 repo 只留結構與範例，不含學生照片與作答明細。
