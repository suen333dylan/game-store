#!/usr/bin/env python3
"""
開發者伺服器
處理遊戲上傳、更新、下架等操作
"""
import socket
import threading
import json
import os
import shutil
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from database import Database

class DeveloperServer:
    def __init__(self, host='0.0.0.0', port=6001):
        self.host = host
        self.port = port
        self.db = Database()
        self.server_socket = None
        self.running = False
        
    def start(self):
        """啟動開發者伺服器"""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(10)
        self.running = True
        
        print(f"[開發者伺服器] 在 {self.host}:{self.port} 上啟動")
        
        while self.running:
            try:
                client_socket, addr = self.server_socket.accept()
                print(f"[開發者伺服器] 新連線: {addr}")
                thread = threading.Thread(target=self.handle_client, args=(client_socket, addr))
                thread.daemon = True
                thread.start()
            except Exception as e:
                if self.running:
                    print(f"[開發者伺服器] 錯誤: {e}")
    
    def receive_full_message(self, client_socket):
        """接收完整的 JSON 訊息（支援大數據）"""
        chunks = []
        while True:
            try:
                chunk = client_socket.recv(65536).decode('utf-8')
                if not chunk:
                    break
                chunks.append(chunk)
                # 嘗試解析 JSON，如果成功則接收完成
                try:
                    full_data = ''.join(chunks)
                    message = json.loads(full_data)
                    return message
                except json.JSONDecodeError:
                    # JSON 未完整，繼續接收
                    continue
            except Exception as e:
                break
        return None
    
    def handle_client(self, client_socket, addr):
        """處理客戶端請求"""
        developer_id = None
        
        try:
            while True:
                message = self.receive_full_message(client_socket)
                if not message:
                    break
                
                msg_type = message.get("type")
                
                if msg_type == "register":
                    response = self.handle_register(message)
                elif msg_type == "login":
                    response = self.handle_login(message)
                    if response["success"]:
                        developer_id = response["developer"]["id"]
                elif msg_type == "upload_game":
                    response = self.handle_upload_game(message, developer_id)
                elif msg_type == "update_game":
                    response = self.handle_update_game(message, developer_id)
                elif msg_type == "deactivate_game":
                    response = self.handle_deactivate_game(message, developer_id)
                elif msg_type == "list_my_games":
                    response = self.handle_list_my_games(developer_id)
                elif msg_type == "upload_files":
                    response = self.handle_upload_files(message, developer_id)
                else:
                    response = {"success": False, "message": "未知的請求類型"}
                
                client_socket.send(json.dumps(response).encode('utf-8'))
                
        except Exception as e:
            print(f"[開發者伺服器] 處理客戶端 {addr} 時發生錯誤: {e}")
        finally:
            client_socket.close()
            print(f"[開發者伺服器] 連線關閉: {addr}")
    
    def handle_register(self, message):
        """處理註冊請求"""
        username = message.get("username")
        password = message.get("password")
        
        if not username or not password:
            return {"success": False, "message": "帳號或密碼不能為空"}
        
        success, msg = self.db.register_developer(username, password)
        return {"success": success, "message": msg}
    
    def handle_login(self, message):
        """處理登入請求"""
        username = message.get("username")
        password = message.get("password")
        
        if not username or not password:
            return {"success": False, "message": "帳號或密碼不能為空"}
        
        success, result = self.db.login_developer(username, password)
        if success:
            return {"success": True, "developer": result}
        else:
            return {"success": False, "message": result}
    
    def handle_upload_game(self, message, developer_id):
        """處理遊戲上傳"""
        if not developer_id:
            return {"success": False, "message": "請先登入"}
        
        game_config = message.get("game_config")
        files_data = message.get("files")
        
        if not game_config or not files_data:
            return {"success": False, "message": "缺少遊戲配置或檔案資料"}
        
        try:
            # 建立遊戲目錄
            game_name = game_config["game_name"]
            version = game_config["version"]
            game_dir = f"uploaded_games/{game_name}/{version}"
            os.makedirs(game_dir, exist_ok=True)
            
            # 儲存遊戲檔案
            for file_info in files_data:
                file_path = os.path.join(game_dir, file_info["name"])
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(file_info["content"])
            
            # 儲存配置檔
            config_path = os.path.join(game_dir, "game_config.json")
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(game_config, f, indent=2, ensure_ascii=False)
            
            # 將遊戲資訊寫入資料庫
            success, result = self.db.create_game(
                game_name=game_name,
                developer_id=developer_id,
                version=version,
                description=game_config.get("description", ""),
                game_type=game_config.get("game_type", "cli"),
                min_players=game_config.get("min_players", 2),
                max_players=game_config.get("max_players", 2),
                server_port=game_config.get("server_port", 5000),
                file_path=game_dir
            )
            
            if success:
                return {"success": True, "message": "遊戲上傳成功", "game_id": result}
            else:
                # 刪除已建立的目錄
                shutil.rmtree(game_dir, ignore_errors=True)
                return {"success": False, "message": result}
                
        except Exception as e:
            return {"success": False, "message": f"上傳失敗: {str(e)}"}
    
    def handle_update_game(self, message, developer_id):
        """處理遊戲更新"""
        if not developer_id:
            return {"success": False, "message": "請先登入"}
        
        game_id = message.get("game_id")
        new_version = message.get("new_version")
        files_data = message.get("files")
        
        if not game_id or not new_version or not files_data:
            return {"success": False, "message": "缺少必要參數"}
        
        try:
            # 獲取遊戲資訊
            game_info = self.db.get_game_by_id(game_id)
            if not game_info:
                return {"success": False, "message": "遊戲不存在"}
            
            # 建立新版本目錄
            game_name = game_info["name"]
            game_dir = f"uploaded_games/{game_name}/{new_version}"
            os.makedirs(game_dir, exist_ok=True)
            
            # 儲存遊戲檔案
            for file_info in files_data:
                file_path = os.path.join(game_dir, file_info["name"])
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(file_info["content"])
            
            # 更新資料庫
            success, msg = self.db.update_game_version(
                game_id, developer_id, new_version, game_dir
            )
            
            if success:
                return {"success": True, "message": "遊戲更新成功"}
            else:
                # 刪除已建立的目錄
                shutil.rmtree(game_dir, ignore_errors=True)
                return {"success": False, "message": msg}
                
        except Exception as e:
            return {"success": False, "message": f"更新失敗: {str(e)}"}
    
    def handle_deactivate_game(self, message, developer_id):
        """處理遊戲下架"""
        if not developer_id:
            return {"success": False, "message": "請先登入"}
        
        game_id = message.get("game_id")
        if not game_id:
            return {"success": False, "message": "缺少遊戲ID"}
        
        success, msg = self.db.deactivate_game(game_id, developer_id)
        return {"success": success, "message": msg}
    
    def handle_list_my_games(self, developer_id):
        """列出開發者的所有遊戲"""
        if not developer_id:
            return {"success": False, "message": "請先登入"}
        
        games = self.db.get_developer_games(developer_id)
        return {"success": True, "games": games}
    
    def handle_upload_files(self, message, developer_id):
        """處理檔案上傳（用於大檔案傳輸）"""
        if not developer_id:
            return {"success": False, "message": "請先登入"}
        
        # 這裡可以實作更複雜的檔案上傳邏輯
        return {"success": True, "message": "檔案上傳功能尚未實作"}
    
    def stop(self):
        """停止伺服器"""
        self.running = False
        if self.server_socket:
            self.server_socket.close()

if __name__ == "__main__":
    host = sys.argv[1] if len(sys.argv) > 1 else '0.0.0.0'
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 6001
    
    server = DeveloperServer(host, port)
    try:
        server.start()
    except KeyboardInterrupt:
        print("\n[開發者伺服器] 正在關閉...")
        server.stop()
