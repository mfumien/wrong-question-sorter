# 00 系統架構 + opencode muse-spark-1.3 設定

## 1. 為什麼這樣切五步

* 拍：解決收件標準化，不然照片歪七扭八後面全錯
* 辨：只做圖→文，不做理解，方便換OCR引擎
* 拆：把一圖多題、多餘閒聊切乾淨，分類才會準
* 分：只打標籤，不出題，避免一次做太多出錯
* 推：只做檢索+排程+變式題，形成複習閉環

## 2. opencode 內建 muse-spark-1.3 設定步驟

本專題LLM統一用 opencode內建，不需另外買Key。

1. 開終端機執行 `opencode --version` 確認已安裝
2. 在本資料夾根目錄放 `opencode.json` (已附)，內容指定：
```json
{
  "model": "opencode/muse-spark-1.3-contributor-free",
  "provider": "opencode"
}
```
3. 在本資料夾執行 `opencode` 進入交談
4. 選模型：輸入 `/models` → 選 `muse-spark-1.3`
5. 驗證：貼上 `03_拆_結構化/拆解Prompt_muse-spark.md` 內的測試題，應回傳合法JSON
6. 學生實作時：02辨用python跑完，把 `output_ocr.json` 的文字貼給opencode，依03/04/05的Prompt逐步執行，不要一次全丟

> 教學提示：muse-spark-1.3 看中文數學式表現穩定，但看圖片較弱，所以02堅持用python本機OCR先轉文字，再餵給spark做理解，這就是0_2的用意。
