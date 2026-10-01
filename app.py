"""app.py - 錯題上傳網頁：手機拍照/截圖上傳 → 自動分類入庫 → 弱點統計.

執行：pip install streamlit && streamlit run app.py
手機連：同一 Wi-Fi 開終端顯示的 Network URL (如 http://192.168.x.x:8501)
"""
import datetime
import os

import streamlit as st

import tools

BASE = os.path.dirname(os.path.abspath(__file__))
INBOX = os.path.join(BASE, "mistakes_images", "待分類")
os.makedirs(INBOX, exist_ok=True)

st.set_page_config(page_title="錯題拍照自動分類", layout="wide")
st.title("錯題拍照自動分類")

with st.sidebar:
    st.subheader("狀態")
    client, model = tools._get_client()
    st.write("Vision：", model if client else "mock演示（未設Key）")
    st.info(tools.get_mistake_stats())

tab1, tab2, tab3 = st.tabs(["拍照上傳", "文字直送", "錯題本"])

with tab1:
    st.caption("手機單拍用相機，一次多張用截圖上傳（可複選），存待分類後逐張分類。")
    shot = st.camera_input("手機拍照（單張）")
    ups = st.file_uploader("或上傳截圖（可多選）", type=["jpg", "jpeg", "png"], accept_multiple_files=True)
    user_answer = st.text_input("學生答案（多張共用，可空）", key="ua1")
    task_id = st.text_input("關聯任務如D01（可空）", key="t1")
    srcs = []
    if shot is not None:
        srcs.append(shot)
    if ups:
        srcs.extend(ups)
    if srcs:
        st.image(srcs, caption=[getattr(s, "name", f"第{i+1}張") for i, s in enumerate(srcs)], width=200)
        if st.button(f"一次分類 {len(srcs)} 張", type="primary"):
            msgs = []
            bar = st.progress(0)
            for i, src in enumerate(srcs):
                ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                safe = getattr(src, "name", "photo.jpg").replace("/", "_")
                tmp = os.path.join(INBOX, f"{ts}_{i:02d}_{safe}")
                with open(tmp, "wb") as f:
                    f.write(src.getbuffer())
                with st.spinner(f"第 {i+1}/{len(srcs)} 張辨識中…"):
                    msgs.append(tools.add_mistake_from_image(tmp, user_answer, task_id))
                bar.progress((i + 1) / len(srcs))
            for m in msgs:
                st.success(m)
            st.rerun()

with tab2:
    text = st.text_area("題目文字（截圖OCR文字可貼這）", height=120)
    ua2 = st.text_input("學生答案（可空）", key="ua2")
    if st.button("文字分類入庫"):
        if not text.strip():
            st.warning("題目空白。")
        else:
            st.success(tools.add_mistake_from_text(text, ua2))

with tab3:
    only_new = st.checkbox("只看未掌握", value=True)
    ms = tools.list_mistakes(only_unmastered=only_new)
    st.write(f"共 {len(ms)} 題")
    for i, m in enumerate(ms):
        title = f"{m.get('subject','?')}-{m.get('unit','?')}-{m.get('knowledge_point','?')}｜{m.get('error_type','?')}"
        with st.expander(f"{i+1}. {title}"):
            st.write("題目：", m.get("question", ""))
            st.write("學生：", m.get("user_answer", ""), "／正解：", m.get("correct_answer", ""))
            st.write("錯因：", m.get("reason", ""), f"(信心{m.get('confidence','')})")
            img = m.get("image", "")
            if img:
                p = os.path.join(BASE, img)
                if os.path.exists(p):
                    st.image(p, use_container_width=True)
            c1, c2 = st.columns(2)
            if c1.button("標為掌握", key=f"m{i}"):
                st.success(tools.set_mastered(i, True))
                st.rerun()
            if c2.button("改回未掌握", key=f"u{i}"):
                st.success(tools.set_mastered(i, False))
                st.rerun()
