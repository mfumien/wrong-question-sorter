"""
04_分 整理：已分類 / 未分類 + 已分類依 科別/章節 分夾 (個人版：進夾即刪上傳區)
- 輸入：02 output_ocr.json + 04 學測截圖_分類輸出.json
- 輸出：根目錄 已分類/<科目>/<單元>/圖片 + 未分類/圖片 + 分類結果總表.csv
- 個人版規則：只要進已分類/未分類，就刪除上傳區原圖 (input_images + File responses + 收件匣)
  老師不查誰交，試算表連結會破是預期的
- 用法：python3 organize.py
  （預設只清 input_images 暫存，保留雲端硬碟同步的 File responses 原圖；
   要連原圖一起刪加 --clean-upload）
"""
import json, csv, shutil, argparse
from pathlib import Path

BASE = Path(__file__).parent.parent
OCR = BASE / "02_辨_python圖轉文" / "output_ocr.json"
CLS = BASE / "04_分_高中分類" / "學測截圖_分類輸出.json"
SRC_DIR = BASE / "02_辨_python圖轉文" / "input_images"
DONE = BASE / "已分類"
TODO = BASE / "未分類"
INBOX = BASE / "01_拍_google表單" / "收件匣_自動同步"


def load_cfg() -> dict:
    """上傳區位置跟 auto_import.py 一樣讀 01_拍_google表單/config.json，
    每人的表單資料夾名不同，不寫死。"""
    p = BASE / "01_拍_google表單" / "config.json"
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


# 上傳區（File responses）路徑來自 config.json 的 form_response_dir
RESP = BASE / load_cfg().get("form_response_dir", "")

def safe(s: str) -> str:
    return s.replace("/", "_").replace("\\", "_").strip()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--clean-upload", action="store_true",
                    help="連同 File responses 原圖與收件匣一併刪除（預設只清 input_images 暫存）")
    args = ap.parse_args()
    ocr = {d["image_file"]: d for d in json.loads(OCR.read_text(encoding="utf-8"))}
    cls = json.loads(CLS.read_text(encoding="utf-8"))
    # 增量整理：保留既有已分類/未分類，只新增本批（重跑不洗掉歷史）
    for d in [DONE, TODO]:
        d.mkdir(parents=True, exist_ok=True)

    # 載入舊總表，用 q_id 合併（新結果覆蓋同 q_id）
    total_csv = BASE / "分類結果總表.csv"
    merged = {}
    if total_csv.exists():
        import csv as _csv
        with open(total_csv, encoding="utf-8-sig") as f:
            for r in _csv.DictReader(f):
                merged[r["q_id"]] = r
    for c in cls:
        # q_id是檔名去副檔名，需還原出原檔名
        qid = c["q_id"]
        # 找出對應圖片 (支援中文空格檔名；上傳區已刪則沿用舊列)
        candidates = list(SRC_DIR.glob(qid + ".*")) if SRC_DIR.exists() else []
        if not candidates and SRC_DIR.exists():
            # fallback：用stem比對
            candidates = [p for p in SRC_DIR.iterdir() if p.stem == qid]
        img = candidates[0] if candidates else None
        o = ocr.get(img.name, {}) if img else {}
        conf = c.get("ocr_confidence", o.get("confidence", 0))
        chars = len(o.get("question_text_raw", "") or c.get("stem_fixed", ""))
        need_retake = o.get("need_retake", False)

        reason = ""
        unclassified_subject = c.get("subject", "") in ("待確認", "未定", "")
        if need_retake or conf < 0.55 or chars < 10 or unclassified_subject:
            if unclassified_subject:
                reason = "查無科目關鍵字，待muse-spark/人工複判（絕不硬猜數學）"
            else:
                reason = f"OCR信心{conf}或字數{chars}不足；{o.get('retake_reason','請重拍')}"
            dest = TODO / (img.name if img else qid)
            if img:
                shutil.copy2(img, dest)
            status = "未分類"
        else:
            subj = safe(c.get("subject", "未定"))
            unit = safe(c.get("unit", "未定"))
            dest_dir = DONE / subj / unit
            dest_dir.mkdir(parents=True, exist_ok=True)
            if img:
                shutil.copy2(img, dest_dir / img.name)
            status = "已分類"
            reason = f"{subj}/{unit}/{c.get('knowledge','')}"

        new_row = {
            "q_id": qid, "image_file": img.name if img else "",
            "狀態": status, "科目": c.get("subject", ""),
            "單元": c.get("unit", ""), "知識點": c.get("knowledge", ""),
            "信心": conf, "原因/路徑": reason if status == "未分類" else f"已分類/{c.get('subject','')}/{c.get('unit','')}/"
        }
        # 上傳區已刪導致找不到圖時，沿用舊列檔名
        if not new_row["image_file"] and qid in merged and merged[qid].get("image_file"):
            new_row["image_file"] = merged[qid]["image_file"]
        merged[qid] = new_row

    # 個人版：進夾即刪上傳區 (input_images + File responses + 收件匣)
    # 預設只清 input_images 暫存；File responses 是雲端硬碟同步原圖，要加 --clean-upload 才刪
    cleaned = []
    zones = [SRC_DIR, RESP, INBOX] if args.clean_upload else [SRC_DIR]
    for qid, r in merged.items():
        name = r["image_file"]
        if not name:
            continue
        for zone in zones:
            p = zone / name
            if p.exists():
                p.unlink()
                cleaned.append(f"{zone.name}/{name}")

    # 總表（累計）
    rows = list(merged.values())
    with open(total_csv, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["q_id", "image_file", "狀態", "科目", "單元", "知識點", "信心", "原因/路徑"])
        w.writeheader()
        w.writerows(rows)

    print(f"本批 {len(cls)} 筆，累計已分類 {sum(1 for r in rows if r['狀態']=='已分類')} / 未分類 {sum(1 for r in rows if r['狀態']=='未分類')}")
    for r in rows:
        print(f"- {r['image_file']} [{r['狀態']}] {r['科目']}/{r['單元']}/{r['知識點']} conf={r['信心']}")
    print(f"總表 → {total_csv}")
    print(f"已分類 → {DONE} / 未分類 → {TODO}")
    print(f"個人版已刪上傳區 {len(cleaned)} 檔：")
    for n in cleaned:
        print(f"  x {n}")

if __name__ == "__main__":
    main()
