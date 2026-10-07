# Skill 說明：wrong-question-sorter（錯題自動分類）

手機拍照 / 截圖上傳錯題，照拍、辨、拆、分、推五步自動分類，
成果進 `已分類/<科目>/<單元>/`，失敗的進 `未分類/`，個人版進夾即刪上傳區。

## 流程與檔案對照

| 步 | 做什麼 | 關鍵檔案 |
|---|---|---|
| 拍 | Google表單收件，每人只改設定 | `01_拍_google表單/config.json`（由 `config.example.json` 複製）、`auto_import.py`（每 N 秒搬新圖）、`archive_input_images.py`（清暫存） |
| 辨 | Python 本機OCR圖轉文 | `02_辨_python圖轉文/ocr_vision.py` → `output_ocr.json` |
| 拆 | LLM拆成結構化JSON | `03_拆_結構化/split.py` + `拆解Prompt_muse-spark.md`（貼進 opencode，模型 `muse-spark-1.3`） |
| 分 | 高中章節+錯因分類並分夾 | `04_分_高中分類/高中各科章節分類體系.json`、`classify.py`、`organize.py` → `已分類/`、`未分類/`、`分類結果總表.csv` |
| 推 | 找類似題+排複習+出變式題 | `05_推_收集推送/push_similar.py` + `變式題Prompt_muse-spark.md` |

Skill 定義給 Agent 讀的在 `.opencode/skills/wrong-question-sorter/SKILL.md`。

## Python 套件與功能

| 套件 | 用在哪 | 功能 |
|---|---|---|
| `rapidocr_onnxruntime` | `ocr_vision.py` | 本機OCR引擎，把照片/截圖轉文字，免 API Key；回傳每行文字+信心分數 |
| `pillow`（PIL） | `ocr_vision.py` | 圖片預處理：RGBA轉白底、長條截圖放大、加白邊、自動對比、銳化 |
| 標準庫 `argparse` | `ocr_vision.py`、`split.py`、`classify.py`、`push_similar.py` | 命令列參數（輸入/輸出路徑） |
| 標準庫 `json` | 全管線 | OCR/拆解/分類結果的存取格式 |
| 標準庫 `re` | `ocr_vision.py`、`split.py`、`classify.py` | 選項切分（A-D）、作答/正解抽取、分類關鍵字命中 |
| 標準庫 `pathlib` | 全管線 | 跨平台路徑、中英文空白檔名處理 |
| 標準庫 `csv` | `push_similar.py`、`organize.py` | 錯題庫讀寫、`分類結果總表.csv` |
| 標準庫 `math`、`collections` | `push_similar.py` | 字元 bigram TF 餘弦相似度（免 sklearn，找類似題） |
| 標準庫 `datetime` | `push_similar.py` | T+1/T+3/T+7 複習日排程 |
| 標準庫 `shutil`、`subprocess`、`time`、`sys` | `auto_import.py`、`organize.py` | 搬圖複製、串跑管線、定時掃描 |

安裝：`pip install -r 02_辨_python圖轉文/requirements.txt`（只需前兩項，其餘內建）。

## 每人要改的只有一檔

`01_拍_google表單/config.json`：`form_url`、`form_response_dir`、`subjects`。
其他腳本、Prompt、分類體系全部共用。
