#!/usr/bin/env python3
"""
錯題本產生器：一次產生完整四層導覽（全部自內容 JSON 重建，可重複執行）

層級：
  1. 錯題.html                              根目錄總表（全部題目，依科目/章節分組）
  2. 已分類/<科目>/<科目>.html              科目頁（各章節與題目清單）
  3. 已分類/<科目>/<單元>/<科目><單元>.html 章節頁（該章節全部題目的完整詳解，可直接列印）
  4. 已分類/<科目>/<單元>/<圖檔名>.html     單題詳解頁（由 詳解HTML產生器.py 產生）

用法：
  python3 05_推_收集推送/錯題本產生器.py
  python3 05_推_收集推送/錯題本產生器.py "05_推_收集推送/詳解內容/batch_*.json"
"""
import html
import json
import sys
import urllib.parse
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
CONTENT_DIR = HERE / "詳解內容"

import importlib.util
_spec = importlib.util.spec_from_file_location("jiexi", HERE / "詳解HTML產生器.py")
jiexi = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(jiexi)

# ---------------------------------------------------------------- 共用樣式
BASE_CSS = jiexi.CSS

NAV_CSS = """
a{color:#1D4ED8;text-decoration:none}
a:hover{text-decoration:underline}
.crumb a{color:#64748B;font-weight:600}
.crumb b{color:#1D4ED8}
.crumb span.sep{color:#CBD5E1;margin:0 6px}
.grid{display:grid;gap:12px}
.g2{grid-template-columns:repeat(auto-fill,minmax(300px,1fr))}
.sbox{background:#FFF;border:1px solid #E2E8F0;border-radius:12px;padding:14px 16px}
.sbox h3{font-size:16px;font-weight:800;margin-bottom:4px}
.sbox .meta{font-size:12px;color:#64748B;margin-bottom:10px}
.qlist{list-style:none;padding:0}
.qlist li{border-top:1px dashed #E2E8F0;padding:9px 0}
.qlist li:first-child{border-top:none}
.qrow{display:flex;gap:10px;align-items:baseline}
.qno{flex:0 0 26px;height:26px;border-radius:8px;background:#1D4ED8;color:#fff;
  font-size:13px;font-weight:800;display:flex;align-items:center;justify-content:center}
.qno.r{background:#15803D}
.qtxt{flex:1;font-size:14.5px;line-height:1.6}
.qtxt .sm{display:block;color:#64748B;font-size:12px;margin-top:3px}
.anschip{display:inline-block;background:#DCFCE7;border:1px solid #86EFAC;color:#14532D;
  font-size:12px;font-weight:800;padding:1px 8px;border-radius:7px;white-space:nowrap}
.pill{display:inline-block;font-size:12px;padding:3px 10px;border-radius:999px;
  background:#EDE9FE;color:#6D28D9;margin:0 6px 6px 0}
.pill.g{background:#DCFCE7;color:#15803D}
.pill.o{background:#FFEDD5;color:#C2410C}
.topbar{display:flex;flex-wrap:wrap;gap:10px;align-items:center;justify-content:space-between;
  margin-bottom:16px}
.btn{font-size:13px;font-weight:700;background:#1D4ED8;color:#FFF;padding:8px 15px;
  border-radius:9px;border:none;cursor:pointer}
.btn.ghost{background:#FFF;color:#1D4ED8;border:1px solid #BFDBFE}
.pnav{display:flex;gap:10px;flex-wrap:wrap;margin-top:22px;padding-top:16px;border-top:1px solid #E2E8F0}
.pnav a{font-size:13px;font-weight:700;background:#FFF;border:1px solid #E2E8F0;
  padding:8px 14px;border-radius:9px}
.sec{margin-bottom:26px}
.sec>h2{font-size:19px;font-weight:800;margin-bottom:4px;display:flex;align-items:center;gap:9px}
.sec>h2 .dot{width:9px;height:9px;border-radius:50%;background:#1D4ED8}
.sec>.sub{font-size:13px;color:#64748B;margin-bottom:12px}
table.tb{width:100%;border-collapse:collapse;font-size:14px;background:#FFF;
  border:1px solid #E2E8F0;border-radius:12px;overflow:hidden}
table.tb th{background:#F8FAFC;text-align:left;font-size:12.5px;color:#475569;
  padding:9px 12px;border-bottom:1px solid #E2E8F0;font-weight:800}
table.tb td{padding:9px 12px;border-bottom:1px solid #F1F5F9}
table.tb tr:last-child td{border-bottom:none}
table.tb a{font-weight:700}
.hero{background:linear-gradient(135deg,#1D4ED8,#6D28D9);color:#FFF;border-radius:16px;
  padding:22px 24px;margin-bottom:20px}
.hero h1{font-size:24px;font-weight:800;margin-bottom:6px}
.hero p{font-size:13.5px;opacity:.9}
.stats{display:flex;gap:22px;flex-wrap:wrap;margin-top:14px}
.stats .s b{font-size:22px;font-weight:800;display:block}
.stats .s span{font-size:12px;opacity:.85}
@media print{
  .topbar,.pnav,.btn{display:none}
  .hero{background:#FFF;color:#0F172A;border:1px solid #CBD5E1}
  .sec{break-before:page}
  .sec:first-of-type{break-before:auto}
}
"""

PAGE_CSS = BASE_CSS + NAV_CSS


def e(t) -> str:
    return html.escape(str(t), quote=False)


def rel_link(from_file: Path, to_file: Path) -> str:
    """相對路徑 + percent-encode，確保中文與空白檔名的連結有效"""
    rel = Path("..") / Path(to_file).relative_to(BASE) if False else None
    import os
    rp = os.path.relpath(to_file, from_file.parent)
    return urllib.parse.quote(rp.replace(os.sep, "/"))


def crumb_html(parts: list) -> str:
    """parts: [(文字, 連結或None)]"""
    out = []
    for i, (text, link) in enumerate(parts):
        sep = '<span class="sep">›</span>' if i else ""
        if link:
            out.append(f'{sep}<a href="{link}">{e(text)}</a>')
        else:
            out.append(f'{sep}<b>{e(text)}</b>')
    return '<div class="crumb">' + "".join(out) + "</div>"


def page(title: str, crumb: str, body: str, extra_head: str = "") -> str:
    return f"""<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)}</title>
<style>{PAGE_CSS}</style>
{extra_head}
</head>
<body>
<div class="wrap">
{crumb}
{body}
<div class="foot">高中錯題分類系統｜拍辨拆分推</div>
</div>
</body>
</html>
"""


# ---------------------------------------------------------------- 載入內容
def load_records(patterns: list) -> list:
    files = []
    for pat in patterns:
        files += sorted(CONTENT_DIR.glob(pat))
    recs = []
    for f in files:
        data = json.loads(f.read_text(encoding="utf-8"))
        recs += data
    return recs


def page_path_for(rec) -> Path:
    """單題詳解頁路徑"""
    img = BASE / rec["image_path"]
    if rec.get("html_name"):
        return img.parent / rec["html_name"]
    return img.with_suffix(".html")


# ---------------------------------------------------------------- 章節頁
def build_chapter(subject: str, unit: str, items: list, master: Path) -> Path:
    folder = (BASE / "已分類" / subject / unit).resolve()
    out = folder / f"{subject}{unit}.html"
    master_rel = rel_link(out, master)

    secs = []
    for i, it in enumerate(items, 1):
        qpage = page_path_for(it)
        q_rel = rel_link(out, qpage)
        opts = it.get("options") or []
        opt_html = ""
        if opts:
            right = {str(x).strip().upper() for x in it.get("right_options", [])}
            wrong = {str(x).strip().upper() for x in it.get("wrong_options", [])}
            li = []
            for o in opts:
                label, body = jiexi.split_opt(o)
                cls = ""
                if label and label in right:
                    cls = ' class="right"'
                elif label and label in wrong:
                    cls = ' class="wrong"'
                k = f'<span class="k">{e(label)}</span>' if label else ""
                li.append(f"<li{cls}>{k}{e(body)}</li>")
            opt_html = '<ol class="opts">' + "".join(li) + "</ol>"

        steps = "".join(f"<li>{e(s)}</li>" for s in it.get("solution", []))
        pits = it.get("pitfalls") or []
        warn = ('<div class="warn"><div class="lab">防錯提醒</div><ul>'
                + "".join(f"<li>{e(p)}</li>" for p in pits) + "</ul></div>") if pits else ""
        note = f'<div class="note">{e(it["note"])}</div>' if it.get("note") else ""
        sa = it.get("student_answer")
        sa_html = (f'<div class="sa"><span class="k">學生作答</span>{e(sa)}</div>') if sa else ""
        chips = [f'<span class="pill">{e(it.get("knowledge",""))}</span>',
                 f'<span class="pill o">錯因：{e(it.get("error_type",""))}</span>',
                 f'<span class="pill g">難度：{e(it.get("difficulty",""))}</span>']
        ans = it.get("answer", "")
        title = it.get("title") or ""

        secs.append(f"""
<div class="card">
  <div class="lab">第 {i} 題　{e(title)}</div>
  <div class="stem">{e(it.get("stem",""))}</div>
  {opt_html}
  {sa_html}
  <div class="lab" style="margin-top:14px">正解</div>
  <div class="ans">{e(ans)}</div>
  <div class="lab" style="margin-top:14px">詳解</div>
  <ol class="steps">{steps}</ol>
  {warn}
  {note}
  <div style="margin-top:12px"><a href="{q_rel}" style="font-size:13px;font-weight:700">→ 開啟單題詳解頁（含原題圖）</a></div>
</div>""")

    body = f"""
<div class="topbar">
  <div><h1>{e(subject)}／{e(unit)}</h1>
  <div class="crumb">{len(items)} 題・知識點：{e("、".join(sorted({i.get("knowledge","") for i in items})))}</div></div>
  <div><button class="btn" onclick="window.print()">列印本頁</button>
  <a class="btn ghost" href="{master_rel}" style="margin-left:6px">回到錯題總表</a></div>
</div>
{"".join(secs)}
<div class="pnav">
  <a href="{master_rel}">← 錯題總表</a>
  <a href="{rel_link(out, (BASE/'已分類'/subject/f'{subject}.html'))}">← {e(subject)} 科目頁</a>
</div>
"""
    out.write_text(page(f"{subject}／{unit}｜錯題詳解本", crumb_html([
        ("錯題本", master_rel), (subject, rel_link(out, BASE / "已分類" / subject / f"{subject}.html")), (unit, None)]), body),
        encoding="utf-8")
    return out


# ---------------------------------------------------------------- 科目頁
def build_subject(subject: str, units: dict, master: Path) -> Path:
    folder = (BASE / "已分類" / subject).resolve()
    out = folder / f"{subject}.html"
    master_rel = rel_link(out, master)

    total = sum(len(v) for v in units.values())
    cards = []
    for unit, items in units.items():
        chapter_page = folder / unit / f"{subject}{unit}.html"
        ch_rel = rel_link(out, chapter_page)
        qrows = []
        for it in items:
            q_rel = rel_link(out, page_path_for(it))
            stem1 = (it.get("stem") or "").strip().split("\n")[0]
            qrows.append(
                f'<li><div class="qrow"><span class="qno">{len(qrows)+1}</span>'
                f'<span class="qtxt">{e(stem1[:70])}'
                f'<span class="sm">{e(it.get("title",""))}｜知識點：{e(it.get("knowledge",""))}'
                f'｜錯因：{e(it.get("error_type",""))}</span></span>'
                f'<span class="anschip">{e(it.get("answer",""))}</span>'
                f'<a href="{q_rel}" style="font-size:12px;font-weight:700">詳解</a></div></li>')
        cards.append(f"""
<div class="sbox">
  <h3><a href="{ch_rel}">{e(subject)}／{e(unit)} 章節詳解本</a></h3>
  <div class="meta">{len(items)} 題・開啟章節頁可一次列印全部題目</div>
  <ul class="qlist">{"".join(qrows)}</ul>
</div>""")

    body = f"""
<div class="topbar">
  <div><h1>{e(subject)}</h1><div class="crumb">{len(units)} 個章節・共 {total} 題</div></div>
  <div><a class="btn ghost" href="{master_rel}">← 回到錯題總表</a></div>
</div>
<div class="grid g2">{"".join(cards)}</div>
<div class="pnav"><a href="{master_rel}">← 錯題總表</a></div>
"""
    out.write_text(page(f"{subject}｜錯題本", crumb_html([("錯題本", master_rel), (subject, None)]), body), encoding="utf-8")
    return out


# ---------------------------------------------------------------- 總表頁
def build_master(groups: dict, master: Path) -> Path:
    total = sum(len(v) for u in groups.values() for v in u.values())
    n_units = sum(len(v) for v in groups.values())

    secs = []
    idx = 0
    for subject, units in groups.items():
        subj_page = BASE / "已分類" / subject / f"{subject}.html"
        subj_rel = rel_link(master, subj_page)
        usecs = []
        for unit, items in units.items():
            ch_page = BASE / "已分類" / subject / unit / f"{subject}{unit}.html"
            ch_rel = rel_link(master, ch_page)
            qrows = []
            for it in items:
                idx += 1
                q_rel = rel_link(master, page_path_for(it))
                stem1 = (it.get("stem") or "").strip().split("\n")[0]
                qrows.append(
                    f'<tr><td style="color:#94A3B8;width:34px">{idx}</td>'
                    f'<td><a href="{q_rel}">{e(stem1[:58])}</a>'
                    f'<div style="font-size:12px;color:#64748B;margin-top:2px">'
                    f'{e(it.get("title",""))}</div></td>'
                    f'<td style="white-space:nowrap">{e(it.get("knowledge",""))}</td>'
                    f'<td style="white-space:nowrap"><span class="anschip">{e(it.get("answer",""))}</span></td>'
                    f'<td style="white-space:nowrap"><a href="{ch_rel}">章節頁</a></td></tr>')
            usecs.append(f"""
<div class="sbox" style="margin-bottom:12px">
  <h3><a href="{ch_rel}">{e(subject)}／{e(unit)}</a> <span class="pill">{len(items)} 題</span></h3>
  <div class="meta">章節詳解本：<a href="{ch_rel}">{e(subject)}{e(unit)}.html</a>（可整章列印）</div>
  <table class="tb"><thead><tr><th>#</th><th>題目</th><th>知識點</th><th>正解</th><th></th></tr></thead>
  <tbody>{"".join(qrows)}</tbody></table>
</div>""")
        secs.append(f"""
<div class="sec">
  <h2><span class="dot"></span><a href="{subj_rel}">{e(subject)}</a>
    <span class="pill g">{sum(len(v) for v in units.values())} 題</span>
    <span class="pill">科目頁</span></h2>
  <div class="sub">{len(units)} 個章節</div>
  {"".join(usecs)}
</div>""")

    # 科目總覽表
    rows = []
    for subject, units in groups.items():
        subj_page = BASE / "已分類" / subject / f"{subject}.html"
        rows.append(f'<tr><td><a href="{rel_link(master, subj_page)}">{e(subject)}</a></td>'
                    f'<td>{len(units)}</td><td>{sum(len(v) for v in units.values())}</td>'
                    f'<td>' + "、".join(f'<a href="{rel_link(master, BASE/"已分類"/subject/u/f"{subject}{u}.html")}">{e(u)}</a>'
                                        for u in units) + '</td></tr>')

    body = f"""
<div class="hero">
  <h1>高中錯題本</h1>
  <p>拍辨拆分推五步流程產出・依科目與章節分層・每一題都有步驟化詳解與防錯提醒</p>
  <div class="stats">
    <div class="s"><b>{len(groups)}</b><span>科目</span></div>
    <div class="s"><b>{n_units}</b><span>章節</span></div>
    <div class="s"><b>{total}</b><span>題目</span></div>
  </div>
</div>
<div class="sec">
  <h2><span class="dot"></span>科目總覽</h2>
  <div class="sub">點科目 → 章節 → 題目，逐層點進去</div>
  <table class="tb"><thead><tr><th>科目</th><th>章節數</th><th>題數</th><th>章節</th></tr></thead>
  <tbody>{"".join(rows)}</tbody></table>
</div>
{"".join(secs)}
<div class="pnav"><a href="{rel_link(master, BASE/'已分類')}">已分類 資料夾</a></div>
"""
    out = master
    out.write_text(page("高中錯題本｜全部錯題詳解", crumb_html([("錯題本", None)]), body), encoding="utf-8")
    return out


# ---------------------------------------------------------------- 主流程
def main() -> None:
    pats = sys.argv[1:] or ["batch_*.json"]
    recs = load_records(pats)
    if not recs:
        print("沒有讀到任何內容 JSON")
        sys.exit(1)

    # 1) 單題詳解頁
    for rec in recs:
        jiexi_out = page_path_for(rec)
        jiexi_out.write_text(jiexi.render(rec), encoding="utf-8")

    # 2) 分組
    groups = {}
    for rec in recs:
        groups.setdefault(rec["subject"], {}).setdefault(rec["unit"], []).append(rec)

    master = BASE / "錯題.html"
    build_master(groups, master)
    print(f"→ {master.relative_to(BASE)}  ({sum(len(v) for u in groups.values() for v in u.values())} 題)")

    for subject, units in groups.items():
        p = build_subject(subject, units, master)
        print(f"→ {p.relative_to(BASE)}  ({sum(len(v) for v in units.values())} 題)")
        for unit, items in units.items():
            c = build_chapter(subject, unit, items, master)
            print(f"   → {c.relative_to(BASE)}  ({len(items)} 題)")

    # 3) 各章節 index.html（沿用單題產生器的索引）
    for subject, units in groups.items():
        for unit, items in units.items():
            folder = BASE / "已分類" / subject / unit
            jiexi.build_index(folder, [{**it, "html_name": page_path_for(it).name} for it in items])
    print("完成")


if __name__ == "__main__":
    main()
