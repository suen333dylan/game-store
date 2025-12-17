#!/bin/bash
# 啟動開發者客戶端

cd "$(dirname "$0")/developer"

if [ $# -eq 0 ]; then
    echo "啟動開發者客戶端 (連線到 localhost:6001)"
    python3 developer_client.py localhost 6001
elif [ $# -eq 1 ]; then
    echo "啟動開發者客戶端 (連線到 $1:6001)"
    python3 developer_client.py $1 6001
else
    echo "啟動開發者客戶端 (連線到 $1:$2)"
    python3 developer_client.py $1 $2
fi
