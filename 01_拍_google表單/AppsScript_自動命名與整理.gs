/**
 * 錯題表單自動整理 - 貼到 試算表 > 擴充功能 > Apps Script
 * 功能：檔名標準化 + 狀態補寫 + 防呆
 * 先跑一次 setupTrigger() 授權
 */
function setupTrigger() {
  ScriptApp.getProjectTriggers().forEach(t => ScriptApp.deleteTrigger(t));
  ScriptApp.newTrigger('onFormSubmit')
    .forSpreadsheet(SpreadsheetApp.getActive())
    .onFormSubmit()
    .create();
}

function onFormSubmit(e) {
  const sheet = e.range.getSheet();
  const row = e.range.getRow();
  const headers = sheet.getRange(1, 1, 1, sheet.getLastColumn()).getValues()[0];
  const idx = n => headers.indexOf(n) + 1;
  const cStu = idx('學號'), cSub = idx('科目'), cStatus = idx('狀態');

  // 1. 補狀態
  if (cStatus > 0 && !sheet.getRange(row, cStatus).getValue()) {
    sheet.getRange(row, cStatus).setValue('待辨識');
  }
  // 2. 檔名標準化：把表單上傳的 Drive 檔改名 學號_科目_日期_列號
  try {
    const stu = sheet.getRange(row, cStu).getValue();
    const sub = sheet.getRange(row, cSub).getValue();
    const date = Utilities.formatDate(new Date(), 'Asia/Taipei', 'yyyyMMdd');
    const urls = sheet.getRange(row, idx('錯題照片連結')).getValue().toString().split(',');
    urls.forEach((u, i) => {
      const m = u.match(/[-\w]{25,}/);
      if (!m) return;
      const f = DriveApp.getFileById(m[0]);
      const ext = f.getName().split('.').pop();
      f.setName(`${stu}_${sub}_${date}_R${row}_${i + 1}.${ext}`);
    });
  } catch (err) { Logger.log(err); }
}
