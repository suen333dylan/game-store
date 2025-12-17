.PHONY: help install start-server start-dev start-player stop clean

help:
	@echo "=========================================="
	@echo "  遊戲商城系統 - Makefile"
	@echo "=========================================="
	@echo ""
	@echo "可用命令："
	@echo "  make install       - 安裝依賴 (uv sync)"
	@echo "  make start-server  - 啟動伺服器"
	@echo "  make start-dev     - 啟動開發者客戶端"
	@echo "  make start-player  - 啟動玩家客戶端"
	@echo "  make stop          - 停止所有伺服器"
	@echo "  make clean         - 清理資料庫和下載檔案"
	@echo ""

install:
	@uv sync

start-server:
	@./start_servers.sh

start-dev:
	@./start_developer_client.sh

start-player:
	@./start_player_client.sh

stop:
	@./stop_servers.sh

clean:
	@echo "正在清理資料..."
	@rm -rf server/database/
	@rm -rf player/downloads/*/
	@echo "✅ 清理完成"
