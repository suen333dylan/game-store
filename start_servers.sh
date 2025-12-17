#!/bin/bash
# 啟動所有伺服器

echo "=========================================="
echo "  啟動遊戲商城伺服器"
echo "=========================================="

cd "$(dirname "$0")"

# 檢查 Python
if ! command -v python3 &> /dev/null; then
    echo "❌ 錯誤：找不到 Python3"
    exit 1
fi

echo ""
echo "正在啟動伺服器..."
echo ""

# 啟動開發者伺服器
echo "[1/2] 啟動開發者伺服器 (埠口 6001)..."
python3 server/developer_server.py 0.0.0.0 6001 &
DEV_SERVER_PID=$!
sleep 1

# 啟動大廳伺服器
echo "[2/2] 啟動大廳伺服器 (埠口 6002)..."
python3 server/lobby_server.py 0.0.0.0 6002 &
LOBBY_SERVER_PID=$!
sleep 1

echo ""
echo "=========================================="
echo "  ✅ 所有伺服器已啟動！"
echo "=========================================="
echo ""
echo "  開發者伺服器: localhost:6001 (PID: $DEV_SERVER_PID)"
echo "  大廳伺服器:   localhost:6002 (PID: $LOBBY_SERVER_PID)"
echo ""
echo "  按 Ctrl+C 停止所有伺服器"
echo "=========================================="
echo ""

# 儲存 PID 供後續使用
echo $DEV_SERVER_PID > /tmp/gamestore_dev_server.pid
echo $LOBBY_SERVER_PID > /tmp/gamestore_lobby_server.pid

# 等待中斷信號
trap "echo ''; echo '正在停止伺服器...'; kill $DEV_SERVER_PID $LOBBY_SERVER_PID 2>/dev/null; echo '✅ 已停止所有伺服器'; exit 0" INT TERM

# 保持腳本運行
wait
