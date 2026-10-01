"""
04_分 高中章節自動分類器 (離線關鍵字版 + muse-spark精修提示)
- 輸入：../03_拆_結構化/範例_拆解輸出.json
- 輸出：範例_分類輸出.json
- 離線版用關鍵字命中體系.json；疑難丟給muse-spark用分類Prompt再判
- 用法：python3 classify.py [輸入] -o 範例_分類輸出.json
"""
import argparse, json, re
from pathlib import Path

def load_taxonomy():
    return json.loads((Path(__file__).parent / "高中各科章節分類體系.json").read_text(encoding="utf-8"))

KEYMAP = [
    (r"二次函數|配方|頂點|判別式", ("數學", "B函數圖形", "二次函數配方求頂點")),
    (r"不等式|象限|x軸|y軸|坐標平面", ("數學", "A數與式", "不等式")),
    (r"平行六面體|外積|平面方程式", ("數學", "D向量矩陣", "內積外積")),
    (r"campfire|rhinoceros|From the camp", ("英文", "D閱讀測驗", "主旨推論")),
    (r"水氣|氣團|大氣|飽和", ("地科", "B大氣海洋", "鋒面氣旋")),
    (r"速度隨時間|v-t|加速度|位移|焦耳|作功|質量.*公斤|汽車", ("物理", "B牛頓力學", "牛頓第二定律")),
    (r"埃及|壁畫|考古|王權|社會分化", ("歷史", "C世界史", "文藝復興")),
    (r"堰塞湖|方位角|河川", ("地理", "B地形氣候", "風化侵蝕")),
    (r"四邊形|AB=\(|平面向量", ("數學", "D向量矩陣", "平面向量")),
    (r"正弦|餘弦|\bsin\b|\bcos\b", ("數學", "C三角比", "正餘弦定理")),
    (r"向量|矩陣|內積", ("數學", "D向量矩陣", "平面向量")),
    (r"機率|期望值", ("數學", "E機率統計", "條件機率")),
    (r"Having|分詞|假設語氣|關係子句|時態", ("英文", "B文法句型", "分詞構句")),
    (r"dreads|stresses|wanders|escapes|shy boy|audiences|speaking before", ("英文", "A字彙片語", "學測高頻字")),
    (r"字根|片語|vocabulary", ("英文", "A字彙片語", "學測高頻字")),
    (r"閱讀|主旨", ("英文", "D閱讀測驗", "主旨推論")),
    (r"牛頓|摩擦", ("物理", "B牛頓力學", "牛頓第二定律")),
    (r"功能|碰撞|動量", ("物理", "C能量動量", "功能定理")),
    (r"電路|庫侖|電磁", ("物理", "D電磁學", "電路分析")),
    (r"指示劑|氫離子|pH|酸鹼", ("化學", "D化學平衡", "pH計算")),
    (r"氧化|莫耳", ("化學", "B化學反應", "酸鹼中和")),
    (r"有機|官能基|異構", ("化學", "C有機化學", "官能基判別")),
    (r"減數分裂|孟德爾|DNA", ("生物", "A細胞遺傳", "孟德爾定律")),
    (r"板塊|岩石", ("地科", "A地球環境", "板塊構造")),
    (r"日治|明鄭|民主化", ("歷史", "A台灣史", "日治政策")),
    (r"等高線|GIS|投影", ("地理", "A地圖GIS", "等高線")),
    (r"憲法|選舉|權力分立", ("公民", "A政治民主", "憲法權力分立")),
]

def guess_error(item):
    t = (item.get("error_point","") + item.get("stem_fixed","")).lower()
    if "符號" in t or "計算" in t or "配方" in t:
        return "計算失誤"
    if "誤把" in t or "觀念" in t or "不清" in t:
        return "概念不清"
    if "沒看到" in t or "漏看" in t:
        return "審題疏漏"
    if "混" in t:
        return "記憶混淆"
    return "概念不清"

def classify_one(item, tax):
    text = item.get("stem_fixed","") + "\n" + " ".join(item.get("options",[]))
    # 先從檔名猜科目 (支援不編檔名，截圖亂碼也沒關係)
    qid = item.get("q_id","")
    subj_hint = None
    for s in tax["科目"].keys():
        if s in qid:
            subj_hint = s
            break
    for pat, (s, u, k) in KEYMAP:
        if re.search(pat, text):
            # 若檔名科目與關鍵字科目衝突，以關鍵字為準但保留提示
            return s, u, k
    # 英文 fallback：英文字符佔比高 → 英文字彙 (處理截圖不編檔名)
    ascii_letters = len(re.findall(r"[A-Za-z]", text))
    cjk = len(re.findall(r"[\u4e00-\u9fff]", text))
    if ascii_letters > 30 and ascii_letters > cjk:
        return "英文", "A字彙片語", "學測高頻字"
    # fallback：用檔名科目 + 該科第一單元第一知識點
    if subj_hint:
        u = list(tax["科目"][subj_hint].keys())[0]
        k = tax["科目"][subj_hint][u][0]
        return subj_hint, u, k
    return "數學", "B函數圖形", "二次函數配方求頂點"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input", nargs="?", default="../03_拆_結構化/範例_拆解輸出.json")
    ap.add_argument("-o", "--output", default="範例_分類輸出.json")
    args = ap.parse_args()
    base = Path(__file__).parent
    inp = (base / args.input) if not Path(args.input).is_absolute() else Path(args.input)
    out = (base / args.output) if not Path(args.output).is_absolute() else Path(args.output)
    tax = load_taxonomy()
    data = json.loads(Path(inp).read_text(encoding="utf-8"))
    res = []
    for d in data:
        s, u, k = classify_one(d, tax)
        d2 = dict(d)
        d2.update({
            "subject": s, "unit": u, "knowledge": k,
            "error_type": guess_error(d),
            "difficulty": "中",
            "reason": f"關鍵字命中 {u}/{k}；錯因依error_point判",
            "review_dates": ["+1天", "+3天", "+7天"]
        })
        res.append(d2)
    out.write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"分類 {len(res)} 題 → {out}")
    for r in res:
        print(f"- {r['q_id']}: {r['subject']}/{r['unit']}/{r['knowledge']} | {r['error_type']}")

if __name__ == "__main__":
    main()
