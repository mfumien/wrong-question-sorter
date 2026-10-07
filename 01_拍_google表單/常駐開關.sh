#!/bin/bash
# 錯題常駐開關：./常駐開關.sh 開|關|狀態
PLIST=~/Library/LaunchAgents/cuoti.autoimport.plist
case "$1" in
  開)
    launchctl load "$PLIST" 2>&1 && echo "常駐已開：傳表單圖後約1分鐘自動進 已分類/"
    ;;
  關)
    launchctl unload "$PLIST" 2>&1 && echo "常駐已關：上傳只會躺著，要手動跑 organize.py"
    ;;
  *)
    if launchctl list | grep -q cuoti.autoimport; then
      echo "狀態：開著中"
      launchctl list | grep cuoti
    else
      echo "狀態：關著"
    fi
    echo "--- 近況 ---"
    tail -3 "01_拍_google表單/auto_import.log" 2>/dev/null || echo "(還沒有log)"
    ;;
esac
