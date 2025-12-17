#!/bin/bash
# 啟動玩家客戶端

cd "$(dirname "$0")/player"

if [ $# -eq 0 ]; then
    echo "啟動玩家客戶端 (連線到 localhost:6002)"
    python3 lobby_client.py localhost 6002
elif [ $# -eq 1 ]; then
    echo "啟動玩家客戶端 (連線到 $1:6002)"
    python3 lobby_client.py $1 6002
else
    echo "啟動玩家客戶端 (連線到 $1:$2)"
    python3 lobby_client.py $1 $2
fi
