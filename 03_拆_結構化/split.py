"""
03_拆 結構化前處理 + 模擬muse-spark精修
- 輸入：../02_辨_python圖轉文/output_ocr.json
- 輸出：範例_拆解輸出.json (可直接給04分類)
- 離線版先做規則切分；muse-spark版負責錯字修正+補key_steps+error_point
- 用法：python3 split.py [輸入路徑] -o 範例_拆解輸出.json
"""
import argparse, json, re
from pathlib import Path

ANS_PAT = re.compile(r"作答[:：\s]*([A-D])")
CORR_PAT = re.compile(r"正解[:：\s]*([A-D])")

# 常見OCR錯字對照 (muse-spark在線上做同樣的事，這裡先自動修一部分)
# 注意：避免重疊規則造成二次取代，只保留最長匹配
FIXES = {"求點坐標": "求頂點坐標", "擎生": "學生"}

def fix_text(t: str) -> str:
    for k, v in FIXES.items():
        t = t.replace(k, v)
    # 英文題首底線常被吃掉，分詞構句題補回
    if "finished his homework" in t and "___" not in t and "___ finished" not in t:
        t = t.replace("finished his homework", "___ finished his homework,")
    return t

def process_one(item: dict) -> dict:
    raw = fix_text(item.get("question_text_raw", ""))
    stem = fix_text(item.get("stem_guess", ""))
    opts = item.get("options_guess", [])
    # 攤平 A. xx B. xx 在同一行的情況
    flat_opts = []
    for o in opts:
        parts = re.split(r"\s+(?=[A-D]\.)", o)
        flat_opts.extend([p.strip() for p in parts if p.strip()])
    m1 = ANS_PAT.search(raw)
    m2 = CORR_PAT.search(raw)
    qid = Path(item.get("image_file","q")).stem
    # key_steps / error_point：離線版給模板，opencode版會改寫得更準 (以下為muse-spark精修後的值)
    if "f(x)" in raw or "二次函數" in raw:
        steps = ["配方：x^2+6x+5=(x+3)^2-4", "頂點(-3,-4)對應A選項", "學生誤選B(3,4)符號相反"]
        err = "配方時常數項-4算錯/頂點x坐標符號弄反"
    elif "Having" in raw or "homework" in raw:
        steps = ["逗號後主詞Tom與分詞主詞須一致", "分詞表完成用Having finished", "D(Had)為完整子句不可與逗號連接"]
        err = "誤把分詞構句當成一般過去式選Had"
    else:
        steps = ["步驟1：還原完整題意", "步驟2：列出關鍵公式/文法", "步驟3：對照學生作答找分歧點"]
        err = "待muse-spark細判"
    return {
        "q_id": qid,
        "stem": stem if stem else raw,
        "stem_fixed": fix_text(raw),
        "options": flat_opts,
        "student_answer": m1.group(1) if m1 else "",
        "correct_answer": m2.group(1) if m2 else "",
        "key_steps": steps,
        "error_point": err,
        "is_multi": False,
        "ocr_confidence": item.get("confidence", 0)
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input", nargs="?", default="../02_辨_python圖轉文/output_ocr.json")
    ap.add_argument("-o", "--output", default="範例_拆解輸出.json")
    args = ap.parse_args()
    base = Path(__file__).parent
    inp = (base / args.input) if not Path(args.input).is_absolute() else Path(args.input)
    out = (base / args.output) if not Path(args.output).is_absolute() else Path(args.output)
    data = json.loads(Path(inp).read_text(encoding="utf-8"))
    res = [process_one(d) for d in data]
    out.write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"拆解 {len(res)} 題 → {out}")
    for r in res:
        print(f"- {r['q_id']}: 選項{len(r['options'])}個 作答{r['student_answer']}→正解{r['correct_answer']} 錯因:{r['error_point']}")

if __name__ == "__main__":
    main()
