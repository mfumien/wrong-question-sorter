"""
05_推 錯題收集 + 類似題推送 (純標準庫，不需pip)
- 輸入：--new 分類輸出.json，--db 錯題庫範例.csv
- 做法：字元bigram TF-IDF餘弦 + 同科目/同知識點加權
- 輸出：推送訊息.md (可貼LINE/Email) + 複習排程
- 用法：python3 push_similar.py --new ../04_分_高中分類/範例_分類輸出.json --db 錯題庫範例.csv
"""
import argparse, json, csv, math
from pathlib import Path
from datetime import date, timedelta
from collections import Counter

def bigrams(s: str):
    s = "".join(s.split()).lower()
    if len(s) < 2:
        return [s]
    return [s[i:i+2] for i in range(len(s)-1)]

def cosine_tf(a: Counter, b: Counter):
    inter = set(a) & set(b)
    dot = sum(a[k]*b[k] for k in inter)
    na = math.sqrt(sum(v*v for v in a.values())) or 1
    nb = math.sqrt(sum(v*v for v in b.values())) or 1
    return dot / (na*nb)

def load_db(path: Path):
    rows = list(csv.DictReader(path.read_text(encoding="utf-8-sig").splitlines()))
    return rows

def similar_for(new_q, db_rows, topk=3):
    n_vec = Counter(bigrams(new_q.get("stem_fixed","")))
    scored = []
    for r in db_rows:
        v = Counter(bigrams(r.get("題幹","")))
        base = cosine_tf(n_vec, v)
        bonus = 0
        if r.get("科目") == new_q.get("subject"):
            bonus += 0.15
        if r.get("知識點") == new_q.get("knowledge"):
            bonus += 0.25
        if r.get("錯因") == new_q.get("error_type"):
            bonus += 0.05
        scored.append((round(base+bonus,3), base, r))
    scored.sort(reverse=True, key=lambda x: x[0])
    return scored[:topk]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--new", default="../04_分_高中分類/範例_分類輸出.json")
    ap.add_argument("--db", default="錯題庫範例.csv")
    ap.add_argument("--out", default="推送範例輸出.md")
    args = ap.parse_args()
    base = Path(__file__).parent
    new_p = (base/args.new) if not Path(args.new).is_absolute() else Path(args.new)
    db_p = (base/args.db) if not Path(args.db).is_absolute() else Path(args.db)
    out_p = (base/args.out) if not Path(args.out).is_absolute() else Path(args.out)
    news = json.loads(new_p.read_text(encoding="utf-8"))
    db = load_db(db_p)
    today = date.today()
    dates = [today+timedelta(days=d) for d in (1,3,7)]
    lines = [f"# 錯題推送報告 ({today.isoformat()} 產生)", ""]
    lines.append(f"本次新錯 {len(news)} 題，庫存 {len(db)} 題。每題推Top3類似題 + T+1/T+3/T+7複習。")
    lines.append("")
    for q in news:
        lines.append(f"## {q['q_id']}｜{q['subject']}/{q['unit']}/{q['knowledge']}｜錯因{q['error_type']}")
        lines.append(f"- 原題：{q['stem_fixed'].replace(chr(10),' / ')}")
        lines.append(f"- 作答{q.get('student_answer')}→正解{q.get('correct_answer')}；錯點：{q.get('error_point')}")
        lines.append(f"- 複習日：{', '.join(d.isoformat() for d in dates)}")
        sims = similar_for(q, db)
        lines.append(f"- 類似題Top3：")
        for score, raw, r in sims:
            lines.append(f"  1. [{r['q_id']}] {r['題幹']} (科目{r['科目']}/{r['知識點']}/相似度{score}) 狀態{r['狀態']}")
        # 高頻警示
        freq = sum(1 for r in db if r.get("知識點")==q.get("knowledge"))
        if freq >= 2:
            lines.append(f"- ⚠️ 高頻弱點：知識點「{q.get('knowledge')}」庫存已有{freq}題，本週加推1變式題")
        lines.append(f"- 變式題 Prompt：見 變式題Prompt_muse-spark.md，把本題stem貼進opencode產1題")
        lines.append("")
    # 統計
    lines.append("## 本週弱點統計")
    cnt = Counter((r["科目"], r["知識點"]) for r in db if r["狀態"]=="待複習")
    for (s,k), c in cnt.most_common(5):
        lines.append(f"- {s}/{k}：{c}題待複習")
    out_p.write_text("\n".join(lines), encoding="utf-8")
    print(f"推送完成 → {out_p}")
    print("\n".join(lines[:20]))

if __name__ == "__main__":
    main()
