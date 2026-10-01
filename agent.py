"""agent.py - 大腦 + Agent 迴圈：讀記憶 -> LLM 決策 -> 調工具 -> 寫記憶.

支援 OpenAI 與 Muse Spark（Meta Model API，OpenAI 相容）：
  pip install openai

  # OpenAI 版：
  export OPENAI_API_KEY=sk-...
  export MODEL=gpt-4o-mini
  python agent.py

  # Muse Spark 版：
  export MODEL_API_KEY=你的MetaKey
  export MODEL=muse-spark-1.3
  python agent.py
"""
import json
import os
import sys

try:
    from openai import OpenAI
except ImportError:
    print("請先執行：pip install openai")
    sys.exit(1)

import tools

# Key 優先順序：MODEL_API_KEY（Muse Spark）> OPENAI_API_KEY
API_KEY = os.getenv("MODEL_API_KEY") or os.getenv("OPENAI_API_KEY")
# 有 MODEL_API_KEY 就預設打到 Meta，否則走 OpenAI 預設網址
BASE_URL = (
    os.getenv("MODEL_BASE_URL")
    or os.getenv("OPENAI_BASE_URL")
    or ("https://api.meta.ai/v1" if os.getenv("MODEL_API_KEY") else None)
)
_default_model = "muse-spark-1.3" if os.getenv("MODEL_API_KEY") else "gpt-4o-mini"
MODEL = os.getenv("MODEL", _default_model)

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "generate_plan",
            "description": "產生 N 天學習計畫並存入 Progress",
            "parameters": {
                "type": "object",
                "properties": {
                    "goal": {"type": "string", "description": "學習目標"},
                    "days": {"type": "integer", "description": "天數，預設14"},
                },
                "required": ["goal"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "log_progress",
            "description": "記錄任務完成分數，自動做補救/跳級判斷",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "description": "如 D01"},
                    "score": {"type": "integer", "description": "0-100"},
                    "note": {"type": "string", "description": "心得或錯因"},
                },
                "required": ["task_id", "score"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_next_task",
            "description": "查詢下一個待辦與完成率",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_progress_summary",
            "description": "查詢整體進度摘要",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_mistake_from_image",
            "description": "拍照錯題入庫：辨識圖片並自動分類寫入Mistakes",
            "parameters": {
                "type": "object",
                "properties": {
                    "image_path": {"type": "string", "description": "圖片路徑"},
                    "user_answer": {"type": "string", "description": "學生答案，可空"},
                    "task_id": {"type": "string", "description": "關聯任務如D01，可空"},
                },
                "required": ["image_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_mistake_stats",
            "description": "查詢弱點Top3與未掌握題數",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_mistake_from_text",
            "description": "截圖文字直送跨科分類入庫：免圖片直接給題目文字",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "題目文字"},
                    "user_answer": {"type": "string", "description": "學生答案"},
                    "task_id": {"type": "string", "description": "關聯任務"},
                },
                "required": ["text"],
            },
        },
    },
]

FUNCS = {
    "generate_plan": tools.generate_plan,
    "log_progress": tools.log_progress,
    "get_next_task": lambda: tools.get_next_task(),
    "get_progress_summary": lambda: tools.get_progress_summary(),
    "add_mistake_from_image": tools.add_mistake_from_image,
    "add_mistake_from_text": tools.add_mistake_from_text,
    "get_mistake_stats": lambda: tools.get_mistake_stats(),
}

SYSTEM = (
    "你是學習教練，繁體中文回覆。每次決策前先看 [記憶] 內的 "
    "Profile/Progress/Mistakes。只能透過工具讀寫進度，不要臆測。"
    "規則：分數<60 加補救並鼓勵；>=90 跳級；不要重教已完成且>=80 的任務。"
    "拍照錯題一律調 add_mistake_from_image 入庫，confidence<0.7 要請學生確認分類。"
)


def read_memory_snippet(limit: int = 4000) -> str:
    try:
        with open(tools.MEM, encoding="utf-8") as f:
            s = f.read()
        return s[:limit]
    except FileNotFoundError:
        return '{"profile":{},"progress":[],"mistakes":[]}'


def main():
    if not API_KEY:
        print("尚未設定 API Key。")
        print("Muse Spark 版：export MODEL_API_KEY=你的MetaKey（https://dev.meta.ai 申請）")
        print("OpenAI 版：export OPENAI_API_KEY=sk-...")
        print("（不連 API 也可先測 tools.py：python3 -c \"import tools; print(tools.get_next_task())\"）")
        return
    client = OpenAI(api_key=API_KEY, base_url=BASE_URL) if BASE_URL else OpenAI(api_key=API_KEY)
    print(f"已連線：{BASE_URL or 'OpenAI預設'} / {MODEL}")
    msgs = [{"role": "system", "content": SYSTEM}]
    print("學習教練啟動（輸入 exit 離開）。試試：")
    print("  我是新手，每天1hr，14天後要展示Agent作品")
    print("  D01完成，80分")
    print("  下一個任務是什麼？")
    while True:
        try:
            q = input("\n> ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n下次見，進度已存在 user_memory.json。")
            break
        if q.lower() in ("exit", "quit", "離開"):
            break
        if not q:
            continue
        msgs.append({
            "role": "user",
            "content": q + f"\n\n[記憶]\n{read_memory_snippet()}",
        })
        resp = client.chat.completions.create(
            model=MODEL, messages=msgs, tools=TOOLS, tool_choice="auto"
        )
        m = resp.choices[0].message
        # 把 assistant（含 tool_calls）寫回歷史
        msgs.append({
            "role": "assistant",
            "content": m.content or "",
            "tool_calls": [
                {
                    "id": c.id,
                    "type": "function",
                    "function": {
                        "name": c.function.name,
                        "arguments": c.function.arguments or "{}",
                    },
                }
                for c in (m.tool_calls or [])
            ] or None,
        })
        if m.tool_calls:
            for c in m.tool_calls:
                name = c.function.name
                try:
                    args = json.loads(c.function.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}
                try:
                    out = FUNCS[name](**args)
                except Exception as e:  # noqa: BLE001
                    out = f"工具 {name} 執行失敗：{e}"
                msgs.append({"role": "tool", "tool_call_id": c.id, "content": str(out)})
            resp2 = client.chat.completions.create(model=MODEL, messages=msgs)
            ans = resp2.choices[0].message.content
            print(ans)
            msgs.append({"role": "assistant", "content": ans})
        else:
            print(m.content)


if __name__ == "__main__":
    main()
