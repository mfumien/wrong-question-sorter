---
name: wrong-question-sorter
description: 錯題拍照自動分類。手機拍照或截圖經拍辨拆分推五步，自動判學科單元知識點與錯因，入庫追蹤弱點。當使用者說錯題分類、拍照入庫、弱點統計時觸發。
---

# Wrong Question Sorter｜錯題拍照自動分類

## What I do

- 手機拍照 / 截圖 → OCR → 結構化 → 雙維度分類 → 入庫 → 弱點統計
- 跨科：國文 / 英文 / 數學 / 物理 / 化學 / 資訊 / 歷史 / 地理
- 雙維度：`學科-單元-知識點` ＋ `錯因六類（概念不清/審題錯誤/計算失誤/思路缺失/記憶混淆/粗心）`
- 圖片永久存檔：`mistakes_images/已分類/<科別>-<單元>/`

## When to use me

- 使用者說「幫我分類」「拍照入庫」「這題錯了」「弱點是什麼」
- `mistakes_images/` 有新圖片時主動分類

## Workflow（拍辨拆分推）

1. **拍**：`add_mistake_from_image(image_path, user_answer, task_id)`，或文字直送 `add_mistake_from_text(text, user_answer, task_id)`
2. **辨**：`vision_ocr()` — PIL 壓到 1024px / JPEG 80% 再丟 Vision LLM；無 Key 回 mock 先測流程
3. **拆**：`llm_classify()` 用 CLASSIFY_PROMPT 強制 JSON + `response_format=json_object`
4. **分**：錯因不在表內歸 `概念不清`；`confidence<0.7` 標「請確認」
5. **推**：`get_mistake_stats()` 回分科計數＋弱點 Top3

## Functions（tools.py）

- `add_mistake_from_image(image_path, user_answer="", task_id="")` — 拍照一鍵入庫
- `add_mistake_from_text(text, user_answer="", task_id="")` — 截圖文字直送
- `get_mistake_stats()` — 未掌握題數＋分科＋弱點
- `generate_plan / log_progress / get_next_task / get_progress_summary` — 學習教練原有工具

## Setup

```bash
pip install openai pillow
export MODEL_API_KEY=你的Key   # 或 OPENAI_API_KEY
export MODEL=muse-spark-1.3    # 或 gpt-4o-mini
python agent.py
```

無 Key 也可跑 mock 演示：`python3 -c "import tools; print(tools.llm_classify('F=ma計算'))"`

## Data layout

- `user_memory.json` — `mistakes[]` 含 subject/unit/knowledge_point/error_type/confidence/image（相對路徑）
- `mistakes_images/已分類/<科別>-<單元>/` — 壓縮原圖，不推照片時只留 `.gitkeep`
- 新圖丟 `mistakes_images/` → 分類後自動搬到 `已分類/`（見 `_store_image`）

## Example

使用者：「這題F=ma我算錯，幫我入庫」
→ 調 `add_mistake_from_text("牛頓第二定律 F=ma", "a=10")`
→ 回「已入庫：物理-牛頓力學-F=ma應用｜錯因:計算失誤」
