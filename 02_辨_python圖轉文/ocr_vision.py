"""
02_辨 Python 圖轉文 OCR + 視覺理解
- 輸入：input_images/ 內 jpg/png (手機拍照或截圖直接丟進來)
- 輸出：output_ocr.json (給03拆解用)
- 引擎：RapidOCR (本機，不需Key) + PIL 預處理
- 用法：python3 ocr_vision.py [--input input_images --output output_ocr.json]
"""
import argparse
import json
import re
from pathlib import Path
from PIL import Image, ImageOps, ImageEnhance

def preprocess(img_path: Path) -> Image.Image:
    img = Image.open(img_path)
    # RGBA轉白底RGB，避免透明背景干擾
    if img.mode == "RGBA":
        bg = Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[3])
        img = bg
    else:
        img = img.convert("RGB")
    w, h = img.size
    # 長條截圖(高<300)先放大2-3倍，不然RapidOCR抓不到
    if h < 300:
        scale = 600 / h
        img = img.resize((int(w*scale), int(h*scale)))
        w, h = img.size
    # 太小先放大，太糊先增強對比
    if max(w, h) < 1200:
        scale = 1200 / max(w, h)
        img = img.resize((int(w*scale), int(h*scale)))
    # 高度仍不足加白邊，避免切邊
    w, h = img.size
    if h < 400:
        canvas = Image.new("RGB", (w, 400), (255, 255, 255))
        canvas.paste(img, (0, (400-h)//2))
        img = canvas
    img = ImageOps.autocontrast(img, cutoff=1)
    img = ImageEnhance.Sharpness(img).enhance(1.3)
    return img

def run_ocr(img: Image.Image):
    from rapidocr_onnxruntime import RapidOCR
    engine = RapidOCR()
    import numpy as np
    arr = np.array(img)
    result, _ = engine(arr)
    # result可能為None(長條圖/空白)，統一轉空串
    if not result:
        return [], 0.0
    texts = [r[1] for r in result]
    scores = [float(r[2]) for r in result]
    conf = sum(scores)/len(scores) if scores else 0.0
    return texts, round(conf, 3)

OPT_PAT = re.compile(r"^[\s]*[([（]?([A-DABCDabcd1234甲乙丙丁]|\(?[1-4]\))[\.、\)\]]\s*.+")

def split_options(lines):
    options, stem_lines = [], []
    for ln in lines:
        if OPT_PAT.match(ln.strip()) and len(ln.strip()) < 80:
            options.append(ln.strip())
        else:
            stem_lines.append(ln.strip())
    return "\n".join(stem_lines), options

def process_one(img_path: Path):
    img = preprocess(img_path)
    try:
        lines, conf = run_ocr(img)
    except Exception as e:
        lines, conf = [f"[OCR引擎錯誤：{e}]"], 0.0
    stem, options = split_options([l for l in lines if l.strip()])
    raw = "\n".join(lines)
    return {
        "image_file": img_path.name,
        "question_text_raw": raw,
        "stem_guess": stem,
        "options_guess": options,
        "char_count": len(raw),
        "confidence": conf,
        "need_retake": bool(conf < 0.55 or len(raw) < 10),
        "retake_reason": "信心低或文字過少，請重拍：填滿畫面、開燈、只拍一題" if (conf < 0.55 or len(raw) < 10) else ""
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="input_images")
    ap.add_argument("--output", default="output_ocr.json")
    args = ap.parse_args()
    base = Path(__file__).parent
    in_dir = base / args.input
    out_path = base / args.output
    imgs = sorted([p for p in in_dir.glob("*") if p.suffix.lower() in (".jpg",".jpeg",".png",".webp")])
    if not imgs:
        print(f"[提示] {in_dir} 沒有圖片，請把手機拍照/截圖丟進來再跑。")
        print("已產生空範本 output_ocr.json 供03測試。");
        out_path.write_text(json.dumps([], ensure_ascii=False, indent=2), encoding="utf-8")
        return
    results = [process_one(p) for p in imgs]
    out_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"完成 {len(results)} 張 → {out_path}")
    for r in results:
        flag = "需重拍!" if r["need_retake"] else "OK"
        print(f"- {r['image_file']}: conf={r['confidence']} chars={r['char_count']} [{flag}]")

if __name__ == "__main__":
    main()
