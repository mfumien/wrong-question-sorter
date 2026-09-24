# wrong-question-sorter｜錯題拍照自動分類

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
