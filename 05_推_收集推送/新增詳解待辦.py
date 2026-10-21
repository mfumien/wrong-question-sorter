#!/usr/bin/env python3
"""
新增詳解待辦產生器：掃描 已分類/ 底下還沒做詳解的錯題圖，
自動 OCR 並產生一份「待補詳解」的內容 JSON，讓 LLM 接著把正解與詳解補上。

流程：
  1) python3 05_推_收集推送/新增詳解待辦.py        # 掃描 + 產生待辦 JSON
  2) LLM 讀圖解題，把待辦 JSON 裡的 answer/solution/pitfalls/knowledge 補齊
  3) python3 05_推_收集推送/錯題本產生器.py        # 重建四層網頁

用法：
  python3 新增詳解待辦.py                 # 掃描並產生待辦檔
  python3 新增詳解待辦.py --status        # 只看目前還有幾題沒詳解
  python3 新增詳解待辦.py --out 我的待辦.json
"""
import argparse
import json
import sys
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
CONTENT_DIR = HERE / "詳解內容"
IMG_EXT = (".jpg", ".jpeg", ".png", ".webp")

sys.path.insert(0, str(BASE / "02_辨_python圖轉文"))


def load_all_records() -> list:
    recs = []
    for f in sorted(CONTENT_DIR.glob("batch_*.json")):
        try:
            recs += json.loads(f.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"⚠️  {f.name} 解析失敗：{e}", file=sys.stderr)
    return recs


def scan_images() -> list:
    out = []
    for p in sorted((BASE / "已分類").rglob("*")):
        if p.suffix.lower() in IMG_EXT:
            out.append(p)
    return out


def ocr_of(path: Path) -> dict:
    try:
        from ocr_vision import process_one
        return process_one(path)
    except Exception as e:
        return {"question_text_raw": "", "options_guess": [], "confidence": 0.0,
                "need_retake": True, "retake_reason": str(e)}


def skeleton(img: Path, ocr: dict, today: date) -> dict:
    subject = img.parent.parent.name
    unit = img.parent.name
    raw = (ocr.get("question_text_raw") or "").strip()
    return {
        "image_path": str(img.relative_to(BASE)),
        "html_name": "",
        "subject": subject,
        "unit": unit,
        "knowledge": "",
        "error_type": "",
        "difficulty": "",
        "confidence": ocr.get("confidence", 0),
        "title": "",
        "stem": raw,
        "options": ocr.get("options_guess", []),
        "right_options": [],
        "wrong_options": [],
        "answer": "",
        "student_answer": "",
        "solution": [],
        "pitfalls": [],
        "review_dates": [f"T+{d}｜{(today + timedelta(days=d)).isoformat()}" for d in (1, 3, 7)],
        "note": "【待補詳解】請依 05_推_收集推送/詳解HTML產生器.py 開頭的欄位規格補齊："
                "knowledge（只能選高中各科章節分類體系.json 內的詞）、error_type、"
                "answer、solution、pitfalls；stem 若有 OCR 錯字請照原圖校正。",
    }


def is_pending(rec: dict) -> bool:
    """已建檔但還沒詳解（正解空或步驟空）"""
    return not (rec.get("answer") or "").strip() or not rec.get("solution")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--status", action="store_true", help="只顯示統計，不產生檔案")
    ap.add_argument("--out", default="", help="待辦 JSON 輸出檔名（預設 batch_待辦_<日期>.json）")
    args = ap.parse_args()

    recs = load_all_records()
    covered = {r.get("image_path", "") for r in recs}
    pending = [r for r in recs if is_pending(r)]
    imgs = scan_images()
    new_imgs = [p for p in imgs if str(p.relative_to(BASE)) not in covered]

    print(f"已分類圖片 {len(imgs)} 張｜已有詳解內容 {len(recs)} 筆")
    print(f"  已完成詳解：{len(recs) - len(pending)} 筆")
    print(f"  有建檔但待補詳解：{len(pending)} 筆")
    print(f"  還沒建檔的新圖：{len(new_imgs)} 張")
    for r in pending:
        print(f"    待補：{r.get('image_path','')}")
    for p in new_imgs:
        print(f"    新圖：{p.relative_to(BASE)}")

    if args.status:
        return
    if not new_imgs:
        print("\n沒有新圖待建檔。若有「待補詳解」項目，直接編輯既有的 batch_*.json 補上即可。")
        return

    today = date.today()
    out_name = args.out or f"batch_待辦_{today.isoformat()}.json"
    out_path = CONTENT_DIR / out_name
    if out_path.exists():
        # 同名檔已存在就併進去，不覆蓋已填好的內容
        out_name = f"batch_待辦_{today.isoformat()}_{date.today().strftime('%H%M%S')}.json"
        out_path = CONTENT_DIR / out_name

    batch = []
    for p in new_imgs:
        print(f"OCR：{p.relative_to(BASE)}")
        batch.append(skeleton(p, ocr_of(p), today))
    out_path.write_text(json.dumps(batch, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n已產生 {out_path.relative_to(BASE)}（{len(batch)} 題）")
    print("下一步：")
    print("  1) 讀原圖解題，把上面檔案裡的 knowledge/error_type/answer/solution/pitfalls 補齊")
    print(f"  2) python3 05_推_收集推送/錯題本產生器.py   # 重建四層網頁，新題會接續進去")


if __name__ == "__main__":
    main()
