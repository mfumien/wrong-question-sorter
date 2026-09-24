"""tools.py - Function Calling 實作：學習路徑規劃與追蹤的「手」.

所有函式都會讀寫 user_memory.json（長期記憶），
讓 Agent 每次決策前有上下文，做完後留下紀錄。
"""
import json
import os
import datetime
import base64

MEM = os.path.join(os.path.dirname(os.path.abspath(__file__)), "user_memory.json")
IMG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mistakes_images")


def _ensure_img_dir() -> str:
    os.makedirs(IMG_DIR, exist_ok=True)
    return IMG_DIR


def _store_image(image_path: str, subject: str = "未分科", unit: str = "未分單元") -> str:
    """把原圖壓縮存到 mistakes_images/已分類/科別-單元/，回傳相對路徑。"""
    try:
        safe = lambda s, d: "".join(c for c in (s or d) if c.isalnum() or "\u4e00" <= c <= "\u9fff") or d
        folder = os.path.join(IMG_DIR, "已分類", f"{safe(subject,'未分科')}-{safe(unit,'未分單元')}")
        os.makedirs(folder, exist_ok=True)
        today = str(datetime.date.today()).replace("-", "")
        n = len(os.listdir(folder)) + 1
        dst = os.path.join(folder, f"{today}_{safe(subject,'未分科')}_{n:03d}.jpg")
        try:
            from PIL import Image
            img = Image.open(image_path)
            img.thumbnail((1024, 1024))
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            img.save(dst, format="JPEG", quality=80)
        except Exception:
            import shutil
            shutil.copy(image_path, dst)
        return os.path.relpath(dst, os.path.dirname(os.path.abspath(__file__)))
    except Exception:
        return ""

DEFAULT_TOPICS = [
    "什麼是 Agent：定義與範例",
    "Prompt 流程 vs Agent 迴圈",
    "Function Calling 原理",
    "Memory 設計：短期與長期記憶",
    "Coze 實作：No-code 建 Bot",
    "Dify 實作：Agent + Tool",
    "Code 實作：Python Agent 迴圈",
    "追蹤機制：進度表與提醒",
    "動態調整：補救與跳級",
    "期末作品：展示你的學習教練",
]


def _load():
    if not os.path.exists(MEM):
        data = {"profile": {}, "progress": [], "mistakes": []}
        _save(data)
        return data
    with open(MEM, encoding="utf-8") as f:
        return json.load(f)


def _save(data):
    with open(MEM, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def generate_plan(goal: str, days: int = 14) -> str:
    """產生 N 天學習計畫並寫入 Progress（待辦）."""
    db = _load()
    days = max(1, min(int(days), 30))
    topics = (DEFAULT_TOPICS * ((days // len(DEFAULT_TOPICS)) + 1))[:days]
    today = datetime.date.today()
    tasks = []
    for i, title in enumerate(topics, 1):
        tasks.append({
            "date": str(today + datetime.timedelta(days=i - 1)),
            "task_id": f"D{i:02d}",
            "task_title": title,
            "status": "待辦",
            "score": -1,
            "note": "",
        })
    db["profile"] = {**db.get("profile", {}), "goal": goal}
    db["progress"] = tasks
    _save(db)
    preview = "\n".join(f'{t["task_id"]} {t["task_title"]}' for t in tasks[:5])
    return f"已為「{goal}」產生 {days} 天計畫：\n{preview}\n...（完整計畫已存入 Progress）"


def log_progress(task_id: str, score: int, note: str = "") -> str:
    """記錄單一任務進度，核心的動態調整邏輯在此."""
    db = _load()
    task_id = task_id.strip().upper()
    found = None
    for t in db.get("progress", []):
        if t["task_id"].upper() == task_id:
            t["status"] = "完成"
            t["score"] = int(score)
            t["note"] = note
            found = t
            break
    if not found:
        return f"找不到 {task_id}，請先呼叫 get_next_task 查看待辦。"

    today = str(datetime.date.today())
    if int(score) < 60:
        db.setdefault("mistakes", []).append({
            "date": today,
            "task_id": task_id,
            "question": found.get("task_title", ""),
            "user_answer": note,
            "correct_answer": "",
            "reason": "分數<60，需補救",
            "review_date": today,
            "mastered": False,
        })
        msg = f"{task_id} 得 {score} 分，已加入 Mistakes 錯題本。建議：用 15 分鐘補救版重學一次再前進。"
    elif int(score) >= 90:
        msg = f"{task_id} 得 {score} 分，已掌握。下一個待辦可直接挑戰，不需重複練習。"
    else:
        msg = f"{task_id} 得 {score} 分，已記錄。按原計畫前進即可。"
    _save(db)
    return msg


def get_next_task() -> str:
    """找出下一個待辦任務（含完成率統計）."""
    db = _load()
    progress = db.get("progress", [])
    if not progress:
        return "尚無計畫，請先呼叫 generate_plan。"
    done = [t for t in progress if t["status"] == "完成"]
    for t in progress:
        if t["status"] == "待辦":
            rate = len(done) / len(progress) * 100
            return (
                f'進度 {len(done)}/{len(progress)}（{rate:.0f}%）\n'
                f'下一個：{t["task_id"]} {t["task_title"]}（{t["date"]}）'
            )
    scores = [t["score"] for t in done if t["score"] >= 0]
    avg = sum(scores) / len(scores) if scores else 0
    return f"全部完成！共 {len(done)} 項，平均 {avg:.0f} 分。"


def get_progress_summary() -> str:
    """回傳整體進度摘要（給追蹤提醒用）."""
    db = _load()
    progress = db.get("progress", [])
    if not progress:
        return "尚無計畫。"
    done = [t for t in progress if t["status"] == "完成"]
    lines = [f'{t["task_id"]} {t["task_title"]} {t["status"]} {t["score"]}' for t in progress]
    return f'完成 {len(done)}/{len(progress)}\n' + "\n".join(lines)


# ===== 五步：拍辨拆分推 =====
ERROR_TYPES = ["概念不清", "審題錯誤", "計算失誤", "思路缺失", "記憶混淆", "粗心"]
SUBJECTS = ["國文", "英文", "數學", "物理", "化學", "生物", "地科", "資訊", "歷史", "地理"]

CLASSIFY_PROMPT = """你是跨科錯題分類器。先判斷學科（國文/英文/數學/物理/化學/生物/地科/資訊/歷史/地理），
再判斷單元與知識點，只回 JSON：
{"subject":學科,"unit":單元,"knowledge_point":知識點,
"question_type":選擇/填充/計算/問答,"difficulty":1-5整數,
"correct_answer":正確答案或空字串,"reason":20字內錯因,
"error_type":概念不清/審題錯誤/計算失誤/思路缺失/記憶混淆/粗心,
"confidence":0-1小數}
題目：{text}
學生答案：{user_answer}"""


def _get_client():
    try:
        from openai import OpenAI
    except ImportError:
        return None, ""
    key = os.getenv("MODEL_API_KEY") or os.getenv("OPENAI_API_KEY") or ""
    base = os.getenv("MODEL_BASE_URL") or os.getenv("OPENAI_BASE_URL") or (
        "https://api.meta.ai/v1" if os.getenv("MODEL_API_KEY") else None
    )
    model = os.getenv("MODEL", "muse-spark-1.3" if os.getenv("MODEL_API_KEY") else "gpt-4o-mini")
    if not key:
        return None, model
    return (OpenAI(api_key=key, base_url=base) if base else OpenAI(api_key=key)), model


def _compress_image(image_path: str, max_side: int = 1024) -> str:
    """【辨前處理】壓縮轉 base64，省 token。無 PIL 就直接讀原檔。"""
    try:
        from PIL import Image
        import io
        img = Image.open(image_path)
        img.thumbnail((max_side, max_side))
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=80)
        return base64.b64encode(buf.getvalue()).decode()
    except Exception:
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode()


def vision_ocr(image_path: str) -> str:
    """【辨】Vision LLM 直接 OCR。無 Key 則回 mock，方便先測流程。"""
    client, model = _get_client()
    if client is None:
        return "MOCK_OCR：二次函數 y=x^2+2x+1，求頂點。學生寫 (0,1)"
    b64 = _compress_image(image_path)
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": [
            {"type": "text", "text": "逐字轉出題目、手寫答案、圖表說明。只回純文字。"},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
        ]}],
    )
    return resp.choices[0].message.content or ""


def llm_classify(text: str, user_answer: str = "") -> dict:
    """【拆+分】結構化 + 雙維度分類。失敗回預設值不斷線。"""
    client, model = _get_client()
    if client is None:
        return _mock_classify(text, user_answer)
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": CLASSIFY_PROMPT.format(text=text[:2000], user_answer=user_answer)}],
        response_format={"type": "json_object"},
    )
    try:
        d = json.loads(resp.choices[0].message.content or "{}")
    except json.JSONDecodeError:
        d = {}
    if d.get("error_type") not in ERROR_TYPES:
        d["error_type"] = "概念不清"
    d.setdefault("confidence", 0.6)
    return d


def _mock_classify(text: str, user_answer: str = "") -> dict:
    """無 Key 離線演示用：關鍵字判科，證明可跨多科。"""
    t = (text + user_answer)
    if any(k in t for k in ["多項式", "f(x)=", "a,b,c為實數"]):
        return {"subject": "數學", "unit": "多項式", "knowledge_point": "代入特定值求係數比大小",
                "question_type": "選擇", "difficulty": 4, "correct_answer": "a>c>b",
                "reason": "未想到代x=1,3,4求abc", "error_type": "思路缺失", "confidence": 0.55}
    if any(k in t for k in ["抗生素", "抗藥性", "細菌"]):
        return {"subject": "生物", "unit": "演化", "knowledge_point": "天擇與抗藥性實驗設計",
                "question_type": "選擇", "difficulty": 3, "correct_answer": "(A)劑量遞增",
                "reason": "遞增劑量篩選抗藥菌", "error_type": "概念不清", "confidence": 0.55}
    if any(k in t for k in ["206Pb", "207Pb", "鉛", "岩心", "圖15"]):
        return {"subject": "地科", "unit": "環境變遷", "knowledge_point": "圖表判讀與污染趨勢",
                "question_type": "選擇", "difficulty": 4, "correct_answer": "",
                "reason": "需對照圖15判讀比值趨勢", "error_type": "概念不清", "confidence": 0.5}
    if any(k in t for k in ["矩陣", "反矩陣", "A[", "a+b+c"]):
        return {"subject": "數學", "unit": "矩陣", "knowledge_point": "反方陣求矩陣與乘法",
                "question_type": "選擇", "difficulty": 4, "correct_answer": "5",
                "reason": "矩陣乘法第一列加錯", "error_type": "計算失誤", "confidence": 0.55}
    if any(k in t for k in ["log", "對數", "1/2<a<1", "實數a,b"]):
        return {"subject": "數學", "unit": "對數", "knowledge_point": "對數大小比較",
                "question_type": "選擇", "difficulty": 3, "correct_answer": "log(a^2)",
                "reason": "忽略2log a更小", "error_type": "概念不清", "confidence": 0.55}
    if any(k in t for k in ["Function", "Agent", "Python", "IP", "迴圈", "Coze", "Dify"]):
        return {"subject": "資訊", "unit": "Agent應用", "knowledge_point": "Function Calling",
                "question_type": "問答", "difficulty": 3, "correct_answer": "",
                "reason": "工具參數定義錯誤", "error_type": "概念不清", "confidence": 0.55}
    if any(k in t for k in ["牛頓", "加速度", "電阻", "電壓", "力", "F=ma"]):
        return {"subject": "物理", "unit": "牛頓力學", "knowledge_point": "F=ma應用",
                "question_type": "計算", "difficulty": 4, "correct_answer": "",
                "reason": "單位換算漏算", "error_type": "計算失誤", "confidence": 0.55}
    if any(k in t for k in ["have been", "has gone", "tense", "時態", "文法", "單字"]):
        return {"subject": "英文", "unit": "完成式", "knowledge_point": "現在完成式",
                "question_type": "選擇", "difficulty": 2, "correct_answer": "have been",
                "reason": "完成式與過去式混淆", "error_type": "記憶混淆", "confidence": 0.55}
    if any(k in t for k in ["論語", "文言", "背誦", "國文", "詩", "詞"]):
        return {"subject": "國文", "unit": "文言文", "knowledge_point": "論語選讀",
                "question_type": "選擇", "difficulty": 2, "correct_answer": "",
                "reason": "字義誤解", "error_type": "概念不清", "confidence": 0.55}
    return {"subject": "數學", "unit": "二次函數", "knowledge_point": "配方法求頂點",
            "question_type": "填充", "difficulty": 3, "correct_answer": "(-1,0)",
            "reason": "配方符號錯誤", "error_type": "計算失誤", "confidence": 0.5}


def add_mistake_from_text(text: str, user_answer: str = "", task_id: str = "") -> str:
    """截圖文字直送版（免圖片）：自動判科分類並入庫。"""
    if not text.strip():
        return "題目空白。"
    c = llm_classify(text, user_answer)
    db = _load()
    today = str(datetime.date.today())
    db.setdefault("mistakes", []).append({
        "date": today, "task_id": task_id, "image": "",
        "question": text[:500], "user_answer": user_answer,
        "correct_answer": c.get("correct_answer", ""),
        "subject": c.get("subject", ""), "unit": c.get("unit", ""),
        "knowledge_point": c.get("knowledge_point", ""),
        "question_type": c.get("question_type", ""),
        "reason": c.get("reason", ""), "error_type": c.get("error_type", "概念不清"),
        "confidence": c.get("confidence", 0.6),
        "review_date": today, "mastered": False,
    })
    _save(db)
    low = "（信心低，請確認）" if float(c.get("confidence", 0.6)) < 0.7 else ""
    return (f"已入庫{low}：{c.get('subject')}-{c.get('unit')}-{c.get('knowledge_point')}｜"
            f"錯因:{c.get('error_type')}｜{c.get('reason')}")


def add_mistake_from_image(image_path: str, user_answer: str = "", task_id: str = "") -> str:
    """【拍+推】一鍵入口：辨->拆->分->寫入 mistakes。給 Agent 當 tool 用。"""
    if not os.path.exists(image_path):
        return f"找不到圖片 {image_path}。"
    text = vision_ocr(image_path)
    if not text.strip():
        return "辨識空白，請重拍（對焦、補光、裁掉桌面）。"
    c = llm_classify(text, user_answer)
    saved = _store_image(image_path, c.get("subject", "未分科"), c.get("unit", "未分單元"))
    db = _load()
    today = str(datetime.date.today())
    db.setdefault("mistakes", []).append({
        "date": today, "task_id": task_id, "image": saved,
        "question": text[:500], "user_answer": user_answer,
        "correct_answer": c.get("correct_answer", ""),
        "subject": c.get("subject", ""), "unit": c.get("unit", ""),
        "knowledge_point": c.get("knowledge_point", ""),
        "question_type": c.get("question_type", ""),
        "reason": c.get("reason", ""), "error_type": c.get("error_type", "概念不清"),
        "confidence": c.get("confidence", 0.6),
        "review_date": today, "mastered": False,
    })
    _save(db)
    low = "（信心低，請確認）" if float(c.get("confidence", 0.6)) < 0.7 else ""
    return (f"已入庫{low}：{c.get('subject')}-{c.get('unit')}-{c.get('knowledge_point')}｜"
            f"錯因:{c.get('error_type')}｜{c.get('reason')}｜圖:{saved or '存檔失敗'}")


def get_mistake_stats() -> str:
    """【推】弱點 Top3，給複習推播用。跨科：分科統計。"""
    db = _load()
    ms = [m for m in db.get("mistakes", []) if not m.get("mastered")]
    if not ms:
        return "目前無未掌握錯題。"
    from collections import Counter
    top = Counter(f"{m.get('subject','?')}-{m.get('unit','?')}-{m.get('error_type','?')}" for m in ms).most_common(3)
    per_subj = Counter(m.get('subject', '?') for m in ms)
    return (f"未掌握 {len(ms)} 題；分科：" + "、".join(f"{k}({v})" for k, v in per_subj.items())
            + "；弱點：" + "、".join(f"{k}({v})" for k, v in top))


def list_mistakes(only_unmastered: bool = False) -> list:
    """給 Streamlit 用：回傳 mistakes 列表（新到舊）。"""
    db = _load()
    ms = db.get("mistakes", [])
    if only_unmastered:
        ms = [m for m in ms if not m.get("mastered")]
    return list(reversed(ms))


def set_mastered(index_from_new: int, mastered: bool = True) -> str:
    """給 Streamlit 用：按新到舊序號標記掌握。"""
    db = _load()
    ms = db.get("mistakes", [])
    i = len(ms) - 1 - int(index_from_new)
    if 0 <= i < len(ms):
        ms[i]["mastered"] = bool(mastered)
        _save(db)
        return f"第 {index_from_new + 1} 題已標為{'掌握' if mastered else '未掌握'}。"
    return "序號超出範圍。"
