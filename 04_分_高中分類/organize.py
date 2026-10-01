"""
04_分 整理：已分類 / 未分類 + 已分類依 科別/章節 分夾 (個人版：進夾即刪上傳區)
- 輸入：02 output_ocr.json + 04 學測截圖_分類輸出.json
- 輸出：根目錄 已分類/<科目>/<單元>/圖片 + 未分類/圖片 + 分類結果總表.csv
- 個人版規則：只要進已分類/未分類，就刪除上傳區原圖 (input_images + File responses + 收件匣)
  老師不查誰交，試算表連結會破是預期的
- 用法：python3 organize.py
"""
import json, csv, shutil
from pathlib import Path

BASE = Path(__file__).parent.parent
OCR = BASE / "02_辨_python圖轉文" / "output_ocr.json"
CLS = BASE / "04_分_高中分類" / "學測截圖_分類輸出.json"
SRC_DIR = BASE / "02_辨_python圖轉文" / "input_images"
DONE = BASE / "已分類"
TODO = BASE / "未分類"
RESP = BASE / "錯題拍照上傳_學號 (File responses)" / "錯題照片 (File responses)"
INBOX = BASE / "01_拍_google表單" / "收件匣_自動同步"

def safe(s: str) -> str:
    return s.replace("/", "_").replace("\\", "_").strip()

def main():
    ocr = {d["image_file"]: d for d in json.loads(OCR.read_text(encoding="utf-8"))}
    cls = json.loads(CLS.read_text(encoding="utf-8"))
    # 清空重建(保留說明.md，只清圖片)
    for d in [DONE, TODO]:
        d.mkdir(parents=True, exist_ok=True)
        for p in d.rglob("*"):
            if p.is_file() and p.suffix.lower() not in (".md",):
                p.unlink()

    rows = []
    for c in cls:
        # q_id是檔名去副檔名，需還原出原檔名
        qid = c["q_id"]
        # 找出對應圖片 (支援中文空格檔名)
        candidates = list(SRC_DIR.glob(qid + ".*"))
        if not candidates:
            # fallback：用stem比對
            candidates = [p for p in SRC_DIR.iterdir() if p.stem == qid]
        img = candidates[0] if candidates else None
        o = ocr.get(img.name, {}) if img else {}
        conf = c.get("ocr_confidence", o.get("confidence", 0))
        chars = len(o.get("question_text_raw", "") or c.get("stem_fixed", ""))
        need_retake = o.get("need_retake", False)

        reason = ""
        if need_retake or conf < 0.55 or chars < 10:
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

        rows.append({
            "q_id": qid, "image_file": img.name if img else "",
            "狀態": status, "科目": c.get("subject", ""),
            "單元": c.get("unit", ""), "知識點": c.get("knowledge", ""),
            "信心": conf, "原因/路徑": reason if status == "未分類" else f"已分類/{c.get('subject','')}/{c.get('unit','')}/"
        })

    # 個人版：進夾即刪上傳區 (input_images + File responses + 收件匣)
    cleaned = []
    for r in rows:
        name = r["image_file"]
        if not name:
            continue
        for zone in [SRC_DIR, RESP, INBOX]:
            p = zone / name
            if p.exists():
                p.unlink()
                cleaned.append(f"{zone.name}/{name}")

    # 總表
    total_csv = BASE / "分類結果總表.csv"
    with open(total_csv, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["q_id", "image_file", "狀態", "科目", "單元", "知識點", "信心", "原因/路徑"])
        w.writeheader()
        w.writerows(rows)

    print(f"已分類 {sum(1 for r in rows if r['狀態']=='已分類')} / 未分類 {sum(1 for r in rows if r['狀態']=='未分類')}")
    for r in rows:
        print(f"- {r['image_file']} [{r['狀態']}] {r['科目']}/{r['單元']}/{r['知識點']} conf={r['信心']}")
    print(f"總表 → {total_csv}")
    print(f"已分類 → {DONE} / 未分類 → {TODO}")
    print(f"個人版已刪上傳區 {len(cleaned)} 檔：")
    for n in cleaned:
        print(f"  x {n}")

if __name__ == "__main__":
    main()
