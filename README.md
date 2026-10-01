# 錯題自動分類系統 - 總覽 (拍辨拆分推)

> 適用：高中專題 / Agent應用課，LLM 統一用 opencode 內建 `muse-spark-1.3`

## 流程總圖

```
[01拍]手機拍照/截圖
  → Google表單上傳 (學號/科目/照片)
  → Drive收件匣 + Sheets錯題庫(原始列)
  → [02辨]Python ocr_vision.py 圖轉文 (RapidOCR)
  → output_ocr.json
  → [03拆]muse-spark拆解成結構化JSON (一題一切)
  → output_split.json
  → [04分]muse-spark依高中章節+錯因分類
  → output_classified.json + 寫回Sheets
  → [05推]push_similar.py 收集+找類似題+排複習+出變式題
  → 個人錯題本 + LINE/Email推送
```

## 各步對應資料夾

| 步 | 資料夾 | 關鍵產出 | LLM |
|---|---|---|---|
| 0 | 00_系統架構 | 本檔 + opencode.json | muse-spark-1.3 |
| 1 拍 | 01_拍_google表單 | 表單規格 + Apps Script | - |
| 2 辨 | 02_辨_python圖轉文 | ocr_vision.py + output_ocr.json | - (本機OCR) |
| 3 拆 | 03_拆_結構化 | Prompt + split.py + output_split.json | muse-spark-1.3 |
| 4 分 | 04_分_高中分類 | 章節體系.json + classify.py | muse-spark-1.3 |
| 5 推 | 05_推_收集推送 | 錯題庫.csv + push_similar.py | muse-spark-1.3 |

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

全程不需API Key即可跑通；要更高準確率才把OCR文字貼進opencode(muse-spark-1.3)用各資料夾內的Prompt再精修一次。

---

## 輕量版 Agent（舊版，單機快速用）


手機拍照 / 截圖 → 自動分類 → 弱點追蹤。OpenCode Skill，可單獨用，也可掛到學習教練 Agent。

## 快速開始

```bash
pip install -r requirements.txt
export MODEL_API_KEY=你的Key   # 或 OPENAI_API_KEY=sk-...
export MODEL=muse-spark-1.3    # 或 gpt-4o-mini
python agent.py
```

無 Key 演示（離線 mock）：

```bash
python3 -c "import tools; print(tools.llm_classify('牛頓第二定律 F=ma'))"
python3 -c "import tools; print(tools.add_mistake_from_text('log(a^2)比較',''))"
python3 -c "import tools; print(tools.get_mistake_stats())"
```

## 五步流程

拍 → 辨 → 拆 → 分 → 推，詳見 `SKILL.md`。

## 網頁上傳

```bash
python3 -m streamlit run app.py
```

手機拍照（單張）／截圖多選批量分類／錯題本回看。手機用同一 Wi-Fi 的 Network URL。

## 目錄

- `SKILL.md` — skill 定義（給 Agent 讀）
- `tools.py` — Function Calling 實作
- `agent.py` — Agent 迴圈範例
- `app.py` — Streamlit 上傳＋錯題本
- `user_memory.example.json` — 資料格式範本
- `mistakes_images/` — 圖片區（照片不進版控）

## 隱私

`mistakes_images/*`、`*user_memory.json`、`*.pdf`、`*.png/.jpg` 皆已 gitignore，
公開 repo 只留結構與範例，不含學生照片。
