"""
自動把 Google表單上傳的圖拖進 input_images (免手動下載)
原理：表單檔案會進雲端硬碟 → 桌機版Drive自動同步到電腦 → 本腳本每30秒掃一次，有新圖就複製+跑全流程

設定 (只做一次)：
1. 電腦裝「Google雲端硬碟桌面版」並登入你開表單的帳號
2. 在雲端硬碟找到表單的上傳資料夾 (名稱通常=表單名稱)，按右鍵「離線存取」打勾
3. 把那個資料夾的本機路徑貼到下方 SOURCE_DIR (範例已填本機收件匣概念路徑)
4. 跑：python3 auto_import.py (放著不用關)

之後學生一送表單，30秒內自動進 已分類/未分類
"""
import time, shutil, subprocess, sys, json
from pathlib import Path

BASE = Path(__file__).parent.parent

def load_config():
    cfg_path = Path(__file__).parent / "config.json"
    example = Path(__file__).parent / "config.example.json"
    if not cfg_path.exists():
        # 第一次用：從範例複製一份，使用者只改這一檔
        shutil.copy2(example, cfg_path)
        print(f"已產生 {cfg_path}，請改 form_url / form_response_dir 後重跑")
    return json.loads(cfg_path.read_text(encoding="utf-8"))

CFG = load_config()
# 每人不同的東西只在 config.json 改，這裡自動讀
SOURCE_DIR = BASE / CFG.get("form_response_dir", "")
DEST_DIR = BASE / "02_辨_python圖轉文" / "input_images"
POLL = int(CFG.get("poll_seconds", 30))

def safe_copy(src: Path, dst: Path):
    """Drive File Provider擋clonefile系統複製，改用讀寫位元組搬運"""
    with open(src, "rb") as f:
        data = f.read()
    if not data:
        raise OSError("來源0B，同步中")
    with open(dst, "wb") as f:
        f.write(data)

def run_pipeline():
    # 依序跑辨→拆→分→整理，有裝 rapidocr 即可
    cmds = [
        [sys.executable, "../02_辨_python圖轉文/ocr_vision.py"],
        [sys.executable, "../03_拆_結構化/split.py", "../02_辨_python圖轉文/output_ocr.json",
         "-o", "../03_拆_結構化/學測截圖_拆解輸出.json"],
        [sys.executable, "../04_分_高中分類/classify.py", "../03_拆_結構化/學測截圖_拆解輸出.json",
         "-o", "../04_分_高中分類/學測截圖_分類輸出.json"],
        [sys.executable, "../04_分_高中分類/organize.py"],
    ]
    for c in cmds:
        subprocess.run(c, cwd=Path(__file__).parent)

def main():
    SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    DEST_DIR.mkdir(parents=True, exist_ok=True)
    print(f"監控 {SOURCE_DIR} → {DEST_DIR}，每{POLL}秒掃一次 (Ctrl+C停止)")
    print(f"學生表單：https://forms.gle/vhK4JuW7WcL4ZRxP6")
    seen = {p.name for p in DEST_DIR.iterdir() if p.is_file()}
    while True:
        # Drive 有時會收掉空資料夾，每輪都確保存在
        SOURCE_DIR.mkdir(parents=True, exist_ok=True)
        DEST_DIR.mkdir(parents=True, exist_ok=True)
        new = []
        if SOURCE_DIR.exists():
            for p in SOURCE_DIR.iterdir():
                if p.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp") and p.name not in seen:
                    if p.stat().st_size == 0:
                        # Drive佔位檔還沒同步完，下一輪重試
                        print(f"略過0B同步中檔案 {p.name}，下輪重試")
                        continue
                    try:
                        safe_copy(p, DEST_DIR / p.name)
                    except (FileNotFoundError, OSError) as e:
                        # Drive同步中佔位檔會複製失敗，下一輪重試，不記seen
                        print(f"略過同步中檔案 {p.name}，下輪重試：{e}")
                        if (DEST_DIR / p.name).exists() and (DEST_DIR / p.name).stat().st_size == 0:
                            (DEST_DIR / p.name).unlink()
                        continue
                    if (DEST_DIR / p.name).stat().st_size == 0:
                        # 複到0B殘檔就刪掉重來
                        (DEST_DIR / p.name).unlink()
                        print(f"複到0B殘檔已刪，下輪重試 {p.name}")
                        continue
                    seen.add(p.name)
                    new.append(p.name)
        if new:
            print(f"發現 {len(new)} 張新圖：{new}，跑分類...")
            try:
                run_pipeline()
            except Exception as e:
                print(f"管線出錯，下輪重試：{e}")
        time.sleep(POLL)

if __name__ == "__main__":
    main()
