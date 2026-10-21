#!/usr/bin/env python3
"""
自動詳解：分類完成後，自動觸發 LLM 為新錯題寫詳解，並接進四層錯題本網頁。

流程：
  1) 掃描 已分類/ 底下還沒做詳解的圖 → 自動 OCR → 產生「待補詳解」骨架 JSON
  2) 用 `opencode run` 叫 LLM 讀原圖解題，補齊正解與步驟化詳解，輸出完成版 JSON
  3) 重跑 錯題本產生器.py，把新題接進 錯題.html → 科目 → 章節 → 單題

用法：
  python3 05_推_收集推送/自動詳解.py
  python3 05_推_收集推送/自動詳解.py --model opencode/glm-5.3-flash-free
  python3 05_推_收集推送/自動詳解.py --dry-run     # 只產生骨架，不呼叫 LLM
  python3 05_推_收集推送/自動詳解.py --skip-llm     # 只產生骨架並重建網頁
"""
import argparse
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
CONTENT_DIR = HERE / "詳解內容"
WORK_FILE = CONTENT_DIR / "_待辦_工作區.json"   # 不符合 batch_*.json glob，不會被產生器重複吃到

_spec = importlib.util.spec_from_file_location("daiban", HERE / "新增詳解待辦.py")
daiban = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(daiban)

PROMPT = """你要替高中錯題撰寫「詳解內容 JSON」，讓系統自動產生每題的 HTML 詳解頁。

## 步驟（照做，不要跳）

1. 用 read 工具讀取待辦骨架檔：{work}
2. 用 read 工具讀取分類體系：{tax}（knowledge 只能從裡面選，不可自創）
3. 對骨架檔裡的每一筆：
   a. 用 read 工具讀取該筆 `image_path` 指向的原圖（這是圖片，用視覺判讀）
   b. 把 OCR 錯字照原圖校正（OCR 常把「數列」認成「敷列」、「試選」認成「試護」）
   c. 解出正解；**數學/物理/化學題一定要用 bash 跑 python3 驗算**（sympy 或 math），不要只靠心算
   d. 填好每一欄，特別是 knowledge、error_type、answer、solution、pitfalls
4. 用 write 工具把「完成版的 JSON 陣列」寫到：{out}
   陣列長度、每筆的欄位名稱與 `image_path` 都要跟待辦檔完全一致，只更新欄位內容
5. 最後只回覆一行「完成 N 題」，不要貼 JSON 內容

## 欄位規格

{{
  "image_path": "已分類/.../原圖.png",   ← 原樣保留，不可改
  "html_name": "",                       ← 一圖多題時填 "<原檔名去副檔名>-1.html"；只有一題留空
  "subject": "數學", "unit": "A數與式",  ← 依資料夾路徑
  "knowledge": "指對數",                 ← 必須是 04_分_高中分類/高中各科章節分類體系.json 裡、該科目該單元底下的詞
  "error_type": "概念不清",              ← 五選一：概念不清/審題疏漏/計算失誤/記憶混淆/解題策略錯
  "difficulty": "中",                    ← 易/中/難
  "confidence": 0.822,                   ← 沿用骨架值
  "title": "一句話短標題（不含題號）",
  "stem": "完整題幹（含題號，換行用 \\n）",
  "options": ["(A) ...", "(B) ..."],     ← 依原圖
  "right_options": ["A", "B"],           ← 只填選項標籤（去掉括號）
  "wrong_options": ["C", "D"],
  "answer": "正解；多選題寫成 (A)(B) 格式",
  "student_answer": "圖上若有手寫或圈選的學生作答就照填，沒有填空字串",
  "solution": ["步驟1：…", "步驟2：…", "步驟3：…"],   ← 3~6 步，每步寫清用什麼觀念/公式
  "pitfalls": ["防錯提醒1", "防錯提醒2"],              ← 1~3 條，要具體，勿寫「小心作答」
  "review_dates": ["T+1｜…", "T+3｜…", "T+7｜…"],      ← 沿用骨架值
  "note": "選填：不確定或需老師留意之處"
}}

## 品質規則

- **不可杜撰**：圖片看不清或不是題目內容時，不要編造題目。
  改成在 note 寫「圖片無法辨識／需人工確認」，answer 留空，solution 寫一條說明。
- 數學式子用 **Unicode 純文字**（a²、√3、≤、π、θ、°、|a|、×10⁻⁷），
  **不要寫 LaTeX**（不要 $...$、\\frac、\\sqrt、\\vec）。分數寫 (1/2)，向量寫 (3, 4) 或 3i+4j。
- 英文題：選項保留英文原文，詳解用中文說明。國文/歷史/地理/地科：詳解要指出判斷依據的具體句子或現象。
- 多選題 right_options 列全部正解、wrong_options 列全部錯誤選項。
- 只改 {work} 與寫 {out} 兩個檔案，不要動其他檔案。
"""


def find_opencode() -> str:
    exe = shutil.which("opencode")
    if exe:
        return exe
    for c in (Path.home() / ".opencode/bin/opencode", Path("/usr/local/bin/opencode"),
              Path("/opt/homebrew/bin/opencode")):
        if c.exists():
            return str(c)
    raise SystemExit("找不到 opencode 執行檔，請先安裝 opencode 或設好 PATH")


def project_model() -> str:
    try:
        cfg = json.loads((BASE / "opencode.json").read_text(encoding="utf-8"))
        return cfg.get("model") or "opencode/glm-5.3-flash-free"
    except Exception:
        return "opencode/glm-5.3-flash-free"


def build_skeleton() -> list:
    """產生待辦骨架（只放還沒建檔的圖）"""
    recs = daiban.load_all_records()
    covered = {r.get("image_path", "") for r in recs}
    imgs = daiban.scan_images()
    new_imgs = [p for p in imgs if str(p.relative_to(BASE)) not in covered]
    if not new_imgs:
        return []
    from datetime import date
    today = date.today()
    batch = []
    for p in new_imgs:
        print(f"  OCR：{p.relative_to(BASE)}")
        batch.append(daiban.skeleton(p, daiban.ocr_of(p), today))
    WORK_FILE.write_text(json.dumps(batch, ensure_ascii=False, indent=2), encoding="utf-8")
    return batch


def find_output(out_path: Path, image_paths: list) -> Path | None:
    """LLM 有時會用相對路徑或自己取檔名寫出結果，
    找不到預期檔案時就在詳解內容資料夾裡找含這些題目的新檔。"""
    if out_path.exists():
        return out_path
    cands = []
    for f in CONTENT_DIR.glob("*.json"):
        if f.name == WORK_FILE.name:
            continue
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(data, list) or not data:
            continue
        paths = {r.get("image_path", "") for r in data if isinstance(r, dict)}
        if set(image_paths) & paths:
            cands.append((f.stat().st_mtime, f, data))
    if not cands:
        return None
    cands.sort()
    _, f, data = cands[-1]
    # 搬到預期檔名，讓產生器吃到
    shutil.copy2(f, out_path)
    return out_path


def call_llm(out_path: Path, model: str, image_paths: list, retries: int = 2) -> int:
    prompt = PROMPT.format(work=WORK_FILE, out=out_path, tax=BASE / "04_分_高中分類/高中各科章節分類體系.json")
    exe = find_opencode()
    for attempt in range(1, retries + 1):
        cmd = [exe, "run", "--model", model, "--agent", "build", "--dir", str(BASE), prompt]
        print(f"  呼叫 opencode（{model}）解題… 第 {attempt}/{retries} 次", flush=True)
        t0 = time.time()
        try:
            p = subprocess.run(cmd, cwd=str(BASE), capture_output=True, text=True, timeout=3600)
        except subprocess.TimeoutExpired:
            print("  ⚠️ 逾時（>60 分），中止")
            return 0
        dt = time.time() - t0
        out = (p.stdout or "").strip()
        for line in out.splitlines()[-6:]:
            print(f"    | {line}")
        if not out:
            print(f"  ⚠️ opencode 沒有輸出（code {p.returncode}，用時 {dt:.0f} 秒）")
            for line in (p.stderr or "").strip().splitlines()[-6:]:
                print(f"    ! {line}")
        found = find_output(out_path, image_paths)
        if found:
            print(f"  opencode 完成，用時 {dt:.0f} 秒")
            data = json.loads(found.read_text(encoding="utf-8"))
            print(f"  詳解完成 {len(data)} 題 → {found.name}")
            return len(data)
        print(f"  ⚠️ 沒有寫出詳解檔（用時 {dt:.0f} 秒）")
    return 0


def rebuild_site() -> None:
    print("  重建錯題本網頁…")
    subprocess.run([sys.executable, str(HERE / "錯題本產生器.py")], cwd=str(BASE))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="", help="LLM 模型，預設讀 opencode.json 的 model")
    ap.add_argument("--dry-run", action="store_true", help="只產生骨架，不呼叫 LLM")
    ap.add_argument("--skip-llm", action="store_true", help="只產生骨架並重建網頁（不呼叫 LLM）")
    ap.add_argument("--no-rebuild", action="store_true", help="不重建網頁")
    args = ap.parse_args()

    print("① 掃描新錯題…")
    batch = build_skeleton()
    if not batch:
        print("  沒有新圖，所有錯題都已有詳解內容。")
        if not (args.dry_run or args.skip_llm) and not args.no_rebuild:
            rebuild_site()
        return
    print(f"  待補詳解 {len(batch)} 題 → {WORK_FILE.name}")

    if args.dry_run or args.skip_llm:
        print("  （略過 LLM）骨架已備妥，補完欄位後再跑 錯題本產生器.py")
        return

    model = args.model or project_model()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = CONTENT_DIR / f"batch_自動詳解_{ts}.json"
    print("② 觸發 LLM 解題…")
    n = call_llm(out_path, model, [r["image_path"] for r in batch])
    if n == 0:
        print("  詳解未完成，保留骨架檔待人工補齊：", WORK_FILE.name)
        return
    WORK_FILE.unlink(missing_ok=True)
    print(f"  已完成 {n} 題 → {out_path.name}")

    if not args.no_rebuild:
        print("③ 接進錯題本網頁…")
        rebuild_site()
    print("完成。")


if __name__ == "__main__":
    main()
