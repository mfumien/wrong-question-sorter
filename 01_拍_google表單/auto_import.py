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
import time, shutil, subprocess, sys
from pathlib import Path

BASE = Path(__file__).parent.parent
# TODO: 已指向真實表單回應夾，裝Drive桌面版即自動同步
SOURCE_DIR = BASE / "錯題拍照上傳_學號 (File responses)" / "錯題照片 (File responses)"
DEST_DIR = BASE / "02_辨_python圖轉文" / "input_images"
POLL = 30

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
        new = []
        if SOURCE_DIR.exists():
            for p in SOURCE_DIR.iterdir():
                if p.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp") and p.name not in seen:
                    shutil.copy2(p, DEST_DIR / p.name)
                    seen.add(p.name)
                    new.append(p.name)
        if new:
            print(f"發現 {len(new)} 張新圖：{new}，跑分類...")
            run_pipeline()
        time.sleep(POLL)

if __name__ == "__main__":
    main()
