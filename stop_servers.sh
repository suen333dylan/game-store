#!/bin/bash
# 停止所有伺服器

echo "正在停止伺服器..."

# 從 PID 檔案讀取並停止
if [ -f /tmp/gamestore_dev_server.pid ]; then
    DEV_PID=$(cat /tmp/gamestore_dev_server.pid)
    kill $DEV_PID 2>/dev/null && echo "✅ 已停止開發者伺服器 (PID: $DEV_PID)"
    rm /tmp/gamestore_dev_server.pid
fi

if [ -f /tmp/gamestore_lobby_server.pid ]; then
    LOBBY_PID=$(cat /tmp/gamestore_lobby_server.pid)
    kill $LOBBY_PID 2>/dev/null && echo "✅ 已停止大廳伺服器 (PID: $LOBBY_PID)"
    rm /tmp/gamestore_lobby_server.pid
fi

echo "完成！"
