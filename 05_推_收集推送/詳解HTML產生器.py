#!/usr/bin/env python3
"""
05_推 詳解 HTML 產生器：把每道錯題的詳解做成單一 HTML 檔，放進
已分類/<科目>/<單元>/ 資料夾（與原圖同目錄、同名 .html）。

用法：
  python3 05_推_收集推送/詳解HTML產生器.py 05_推_收集推送/詳解內容/batch_1.json
  python3 05_推_收集推送/詳解HTML產生器.py 05_推_收集推送/詳解內容/*.json

輸入 JSON：陣列，每筆欄位
  image_path (必填，相對於專案根目錄)
  subject, unit, knowledge, error_type, difficulty
  stem        題幹文字（可含 <sup>、√、≤ 等符號）
  options     選項陣列（可空）
  answer      正解
  solution    詳解步驟陣列
  pitfalls    防錯提醒陣列
  review_dates 複習日陣列
  note        備註（可選）
"""
import base64
import html
import json
import mimetypes
import re
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent

CSS = """
*{box-sizing:border-box;margin:0;padding:0}
body{background:#F1F5F9;color:#0F172A;
  font-family:"PingFang TC","Noto Sans TC","Microsoft JhHei",-apple-system,sans-serif;
  line-height:1.75;padding:24px 16px 56px}
.wrap{max-width:880px;margin:0 auto}
.crumb{font-size:13px;color:#64748B;margin-bottom:10px}
.crumb b{color:#1D4ED8}
h1{font-size:22px;font-weight:800;letter-spacing:.02em;margin-bottom:12px}
.chips{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:18px}
.chip{font-size:12px;font-weight:700;padding:4px 11px;border-radius:999px;
  background:#DBEAFE;color:#1D4ED8}
.chip.u{background:#DCFCE7;color:#15803D}
.chip.k{background:#EDE9FE;color:#6D28D9}
.chip.e{background:#FFEDD5;color:#C2410C}
.chip.d{background:#E2E8F0;color:#475569}
.card{background:#FFF;border:1px solid #E2E8F0;border-radius:14px;padding:20px 22px;margin-bottom:16px}
.lab{font-size:12px;font-weight:800;color:#64748B;letter-spacing:.08em;margin-bottom:8px}
.stem{font-size:16.5px;white-space:pre-wrap;word-break:break-word}
ol.opts{margin:12px 0 0;padding-left:0;list-style:none}
ol.opts li{padding:7px 12px;margin-bottom:6px;background:#F8FAFC;border:1px solid #E2E8F0;
  border-radius:9px;font-size:15.5px}
ol.opts li.right{background:#DCFCE7;border-color:#86EFAC;color:#14532D;font-weight:700}
ol.opts li.wrong{background:#FEF2F2;border-color:#FEC7C7;color:#991B1B;text-decoration:line-through;opacity:.85}
ol.opts li span.k{font-weight:800;margin-right:8px;color:#475569}
ol.opts li.right span.k{color:#15803D}
ol.opts li.wrong span.k{color:#B91C1C}
.ans{display:inline-block;background:#DCFCE7;border:1px solid #86EFAC;color:#14532D;
  font-weight:800;font-size:15px;padding:7px 16px;border-radius:10px}
.steps{list-style:none;counter-reset:s}
.steps li{counter-increment:s;position:relative;padding:12px 16px 12px 50px;margin-bottom:10px;
  background:#F8FAFC;border:1px solid #E2E8F0;border-radius:11px;font-size:15.5px;white-space:pre-wrap}
.steps li::before{content:counter(s);position:absolute;left:14px;top:12px;width:24px;height:24px;
  border-radius:50%;background:#1D4ED8;color:#fff;font-size:13px;font-weight:800;
  display:flex;align-items:center;justify-content:center}
.warn{background:#FFF7ED;border:1px solid #FDBA74;border-left:5px solid #EA580C;
  border-radius:11px;padding:14px 18px;margin-bottom:16px}
.warn .lab{color:#C2410C}
.warn ul{margin:0;padding-left:20px}
.warn li{margin-bottom:5px;font-size:15px}
.warn li:last-child{margin-bottom:0}
.note{background:#EFF6FF;border:1px solid #BFDBFE;border-left:5px solid #1D4ED8;
  border-radius:11px;padding:13px 18px;font-size:15px;margin-bottom:16px}
.rv{display:flex;flex-wrap:wrap;gap:8px;align-items:center}
.rv .chip{background:#E2E8F0;color:#475569}
.sa{margin-top:14px;padding:9px 14px;background:#FFF7ED;border:1px solid #FDBA74;
  border-radius:10px;font-size:15px;color:#7C2D12}
.sa .k{font-weight:800;color:#C2410C;margin-right:10px}
details{margin-top:4px}
summary{cursor:pointer;font-size:13px;font-weight:700;color:#1D4ED8;padding:8px 0}
figure{margin:10px 0 0}
figure img{max-width:100%;border:1px solid #E2E8F0;border-radius:10px;display:block}
figcaption{font-size:12px;color:#94A3B8;margin-top:6px}
.foot{text-align:center;font-size:12px;color:#94A3B8;margin-top:24px}
@media print{
  body{background:#FFF;padding:0}
  .card{break-inside:avoid;border-color:#CBD5E1}
  details{open:true}
  .warn,.note{break-inside:avoid}
}
"""


def b64_img(path: Path) -> str:
    mime = mimetypes.guess_type(path.name)[0] or "image/png"
    return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode()}"


def img_tag(path: Path) -> str:
    """圖片不存在時給佔位提示，不要讓產生器整批失敗"""
    if not path.exists():
        return (f'<div class="note">原題圖片未隨本repo提供（{html.escape(str(path))}）。'
                f'把圖片放回 {html.escape(str(path.parent.relative_to(BASE)))} 後重跑產生器即可自動內嵌。</div>')
    mime = mimetypes.guess_type(path.name)[0] or "image/png"
    data = base64.b64encode(path.read_bytes()).decode()
    return (f'<img src="data:{mime};base64,{data}" alt="原題">')


def esc(t: str) -> str:
    """只跳脫 < > & ，保留換行；數學上標等 HTML 標記允許保留。"""
    return html.escape(str(t), quote=False)


# 選項標籤：支持 (A) （A） A. A、 A  (數字同理)
_BRACKET = re.compile(r"^\s*[\(（]\s*([A-Za-z1-9])\s*[\)）]\s*(.*)$", re.S)
_DOTTED = re.compile(r"^\s*([A-Za-z])\s*[\.、．]\s+(.*)$", re.S)


def split_opt(text: str) -> tuple[str, str]:
    """回傳 (標籤, 內容)；無標籤時標籤為空字串"""
    s = str(text).strip()
    m = _BRACKET.match(s)
    if m:
        return m.group(1).upper(), m.group(2).strip()
    m = _DOTTED.match(s)
    if m:
        return m.group(1).upper(), m.group(2).strip()
    return "", s


def render(rec: dict) -> str:
    img_rel = rec["image_path"]
    img_path = BASE / img_rel
    opt_html = ""
    opts = rec.get("options") or []
    if opts:
        right = {str(x).strip().upper() for x in rec.get("right_options", [])}
        wrong = {str(x).strip().upper() for x in rec.get("wrong_options", [])}
        li = []
        for o in opts:
            label, body = split_opt(o)
            cls = ""
            if label and label in right:
                cls = ' class="right"'
            elif label and label in wrong:
                cls = ' class="wrong"'
            k = f'<span class="k">{html.escape(label)}</span>' if label else ""
            li.append(f"<li{cls}>{k}{esc(body)}</li>")
        opt_html = '<ol class="opts">' + "".join(li) + "</ol>"

    steps = "".join(f"<li>{esc(s)}</li>" for s in rec.get("solution", []))
    pitfalls = rec.get("pitfalls") or []
    warn = ""
    if pitfalls:
        warn = ('<div class="warn"><div class="lab">防錯提醒</div><ul>'
                + "".join(f"<li>{esc(p)}</li>" for p in pitfalls) + "</ul></div>")
    note = f'<div class="note">{esc(rec["note"])}</div>' if rec.get("note") else ""
    rv = rec.get("review_dates") or []
    rv_html = ('<div class="rv"><span class="chip">複習日</span>'
               + "".join(f'<span class="chip">{html.escape(str(d))}</span>' for d in rv) + "</div>") if rv else ""

    img_html = ""
    if img_path.exists():
        img_html = (f'<details><summary>原題圖片（{html.escape(img_path.name)}）</summary><figure>'
                    f'{img_tag(img_path)}'
                    f'<figcaption>來源：{html.escape(img_rel)}</figcaption></figure></details>')
    else:
        img_html = f'<div class="lab">原題</div>{img_tag(img_path)}'

    chips = [
        f'<span class="chip">{esc(rec.get("subject",""))}</span>',
        f'<span class="chip u">{esc(rec.get("unit",""))}</span>',
        f'<span class="chip k">{esc(rec.get("knowledge",""))}</span>',
    ]
    if rec.get("error_type"):
        chips.append(f'<span class="chip e">錯因：{esc(rec["error_type"])}</span>')
    if rec.get("difficulty"):
        chips.append(f'<span class="chip d">難度：{esc(rec["difficulty"])}</span>')
    if rec.get("confidence") is not None:
        chips.append(f'<span class="chip d">OCR信心：{rec["confidence"]}</span>')

    title = rec.get("title") or (rec.get("stem", "").strip().split("\n")[0][:40] or img_path.stem)

    sa = rec.get("student_answer")
    sa_html = ""
    if sa:
        sa_html = (f'<div class="sa"><span class="k">學生作答</span>{esc(sa)}</div>')

    return f"""<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}｜{esc(rec.get("subject",""))} {esc(rec.get("unit",""))}</title>
<style>{CSS}</style>
</head>
<body>
<div class="wrap">
  <div class="crumb">錯題本｜<b>{esc(rec.get("subject",""))}</b>｜{esc(rec.get("unit",""))}｜{esc(rec.get("knowledge",""))}</div>
  <h1>{esc(title)}</h1>
  <div class="chips">{''.join(chips)}</div>

  <div class="card">
    <div class="lab">題目</div>
    <div class="stem">{esc(rec.get("stem",""))}</div>
    {opt_html}
    {sa_html}
  </div>

  <div class="card">
    <div class="lab">正解</div>
    <div class="ans">{esc(rec.get("answer",""))}</div>
  </div>

  <div class="card">
    <div class="lab">詳解</div>
    <ol class="steps">{steps}</ol>
  </div>

  {warn}
  {note}

  <div class="card">
    <div class="lab">複習排程</div>
    {rv_html}
  </div>

  <div class="card">
    <div class="lab">原題</div>
    {img_html}
  </div>

  <div class="foot">高中錯題分類系統｜拍辨拆分推</div>
</div>
</body>
</html>
"""


def build_index(unit_dir: Path, items: list) -> None:
    """在每個單元資料夾產生 index.html 索引"""
    by_subject = {}
    for it in items:
        by_subject.setdefault(it.get("subject", ""), []).append(it)
    rows = []
    for it in items:
        f = it["html_name"]
        rows.append(
            f'<li><a href="{html.escape(f, quote=True)}">{html.escape(it.get("title") or f)}</a>'
            f'<span class="tag">{html.escape(str(it.get("knowledge","")))}</span></li>'
        )
    subj = unit_dir.parent.name
    body = f"""<!DOCTYPE html>
<html lang="zh-Hant"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(subj)}｜{html.escape(unit_dir.name)}</title>
<style>{CSS}
ol.opts{{display:none}}
ul.ql{{list-style:none;padding:0}}
ul.ql li{{background:#F8FAFC;border:1px solid #E2E8F0;border-radius:10px;padding:11px 14px;margin-bottom:8px}}
ul.ql li a{{color:#1D4ED8;font-weight:700;text-decoration:none;font-size:15.5px}}
ul.ql li a:hover{{text-decoration:underline}}
.tag{{display:inline-block;margin-left:10px;font-size:12px;color:#6D28D9;background:#EDE9FE;
  padding:2px 9px;border-radius:999px}}
</style></head><body><div class="wrap">
<div class="crumb">錯題本｜<b>{html.escape(subj)}</b>｜{html.escape(unit_dir.name)}</div>
<h1>{html.escape(subj)}／{html.escape(unit_dir.name)}</h1>
<div class="card"><div class="lab">本單元題目（{len(items)} 題）</div>
<ul class="ql">{''.join(rows)}</ul></div>
<div class="foot">高中錯題分類系統｜拍辨拆分推</div>
</div></body></html>
"""
    (unit_dir / "index.html").write_text(body, encoding="utf-8")


def main() -> None:
    files = sys.argv[1:]
    if not files:
        print("用法：python3 詳解HTML產生器.py <內容.json ...>")
        sys.exit(1)
    all_items = []
    for f in files:
        recs = json.loads(Path(f).read_text(encoding="utf-8"))
        for rec in recs:
            img_rel = rec["image_path"]
            img_path = BASE / img_rel
            if rec.get("html_name"):
                out = img_path.parent / rec["html_name"]
            else:
                out = img_path.with_suffix(".html")
            out.write_text(render(rec), encoding="utf-8")
            all_items.append({**rec, "html_name": out.name})
            print(f"→ {out.relative_to(BASE)}")
    # 每個單元資料夾產生 index.html
    groups = {}
    for it in all_items:
        d = (BASE / it["image_path"]).parent
        groups.setdefault(d, []).append(it)
    for d, items in groups.items():
        build_index(d, items)
        print(f"→ {(d / 'index.html').relative_to(BASE)}  ({len(items)} 題)")
    print(f"完成：{len(all_items)} 題")


if __name__ == "__main__":
    main()
