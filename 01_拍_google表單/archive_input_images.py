"""
安全封存：只清 input_images 暫存，絕不動 File responses 原始夾
- 試算表連結指向的是 File responses 內的檔案ID，本腳本完全不碰該夾，所以連結不會破
- organize.py 用的全是 copy 複製，原檔一直都在
- 用法：python3 archive_input_images.py [--run]，不加--run只預覽
"""
from pathlib import Path
BASE = Path(__file__).parent.parent
SRC = BASE / "02_辨_python圖轉文" / "input_images"
DONE = BASE / "已分類"
TODO = BASE / "未分類"
RESP = BASE / "錯題拍照上傳_學號 (File responses)"

def main(run=False):
    done_names = set()
    for d in [DONE, TODO]:
        if d.exists():
            for p in d.rglob("*"):
                if p.is_file() and p.suffix.lower() in (".jpg",".jpeg",".png",".webp"):
                    done_names.add(p.name)
    cands = [p for p in SRC.iterdir() if p.is_file() and p.name in done_names]
    print(f"File responses 原始夾：{RESP} → 絕不動，試算表連結安全")
    print(f"input_images 共 {len(list(SRC.iterdir()))} 檔，其中已進已分類/未分類 {len(cands)} 檔可封存")
    for p in cands:
        print(f"- {p.name}")
    if run:
        for p in cands:
            p.unlink()
        print(f"已封存 {len(cands)} 檔，input_images 已清空，已分類/未分類不受影響")
    else:
        print("預覽而已，加 --run 才真的刪")

if __name__ == "__main__":
    import sys
    main(run="--run" in sys.argv)
