#!/usr/bin/env python3
"""
大廳伺服器
處理玩家登入、遊戲列表、房間管理等
"""
import socket
import threading
import json
import os
import sys
import subprocess
import time
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from database import Database

class Room:
    """房間類別"""
    def __init__(self, room_id, game_id, game_info, host_player):
        self.room_id = room_id
        self.game_id = game_id
        self.game_info = game_info
        self.host_player = host_player
        self.players = [host_player]
        self.status = "waiting"  # waiting, playing, finished
        self.game_server_process = None
        self.server_port = None  # 實際運行的埠口
        self.created_at = time.time()
        
    def add_player(self, player):
        """新增玩家到房間"""
        if len(self.players) < self.game_info["max_players"]:
            self.players.append(player)
            return True
        return False
    
    def remove_player(self, player_id):
        """移除玩家"""
        self.players = [p for p in self.players if p["id"] != player_id]
        
    def is_full(self):
        """檢查房間是否已滿"""
        return len(self.players) >= self.game_info["max_players"]
    
    def can_start(self):
        """檢查是否可以開始遊戲"""
        return len(self.players) >= self.game_info["min_players"]
    
    def to_dict(self):
        """轉換為字典"""
        return {
            "room_id": self.room_id,
            "game_id": self.game_id,
            "game_name": self.game_info["name"],
            "host": self.host_player["username"],
            "players": [p["username"] for p in self.players],
            "player_count": len(self.players),
            "max_players": self.game_info["max_players"],
            "min_players": self.game_info["min_players"],
            "status": self.status
        }

class LobbyServer:
    def __init__(self, host='0.0.0.0', port=6002):
        self.host = host
        self.port = port
        self.db = Database()
        self.server_socket = None
        self.running = False
        self.rooms = {}  # {room_id: Room}
        self.next_room_id = 1
        self.online_players = {}  # {player_id: socket}
        self.player_rooms = {}  # {player_id: room_id}
        self.lock = threading.RLock()
        
    def start(self):
        """啟動大廳伺服器"""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(50)
        self.running = True
        
        print(f"[大廳伺服器] 在 {self.host}:{self.port} 上啟動")
        
        while self.running:
            try:
                client_socket, addr = self.server_socket.accept()
                print(f"[大廳伺服器] 新連線: {addr}")
                thread = threading.Thread(target=self.handle_client, args=(client_socket, addr))
                thread.daemon = True
                thread.start()
            except Exception as e:
                if self.running:
                    print(f"[大廳伺服器] 錯誤: {e}")
    
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
    
    def broadcast_to_room(self, room_id, message, exclude_player_id=None):
        """廣播訊息給房間內的所有玩家"""
        with self.lock:
            room = self.rooms.get(room_id)
            if not room:
                return
            
            for player in room.players:
                if player["id"] == exclude_player_id:
                    continue
                
                player_info = self.online_players.get(player["id"])
                if player_info:
                    try:
                        sock = player_info["socket"]
                        sock.send(json.dumps(message).encode('utf-8'))
                    except Exception as e:
                        print(f"[大廳伺服器] 發送廣播失敗: {e}")

    def handle_client(self, client_socket, addr):
        """處理客戶端請求"""
        player_id = None
        
        try:
            while True:
                message = self.receive_full_message(client_socket)
                if not message:
                    break
                
                msg_type = message.get("type")
                
                if msg_type == "register":
                    response = self.handle_register(message)
                elif msg_type == "login":
                    response = self.handle_login(message, client_socket)
                    if response["success"]:
                        player_id = response["player"]["id"]
                elif msg_type == "list_games":
                    response = self.handle_list_games()
                elif msg_type == "get_game_detail":
                    response = self.handle_get_game_detail(message)
                elif msg_type == "download_game":
                    response = self.handle_download_game(message, player_id)
                elif msg_type == "create_room":
                    response = self.handle_create_room(message, player_id)
                elif msg_type == "list_rooms":
                    response = self.handle_list_rooms()
                elif msg_type == "join_room":
                    response = self.handle_join_room(message, player_id)
                elif msg_type == "leave_room":
                    response = self.handle_leave_room(player_id)
                elif msg_type == "start_game":
                    response = self.handle_start_game(player_id)
                elif msg_type == "get_room_status":
                    response = self.handle_get_room_status(player_id)
                elif msg_type == "add_rating":
                    response = self.handle_add_rating(message, player_id)
                elif msg_type == "get_ratings":
                    response = self.handle_get_ratings(message)
                else:
                    response = {"success": False, "message": "未知的請求類型"}
                
                client_socket.send(json.dumps(response).encode('utf-8'))
                
        except Exception as e:
            print(f"[大廳伺服器] 處理客戶端 {addr} 時發生錯誤: {e}")
        finally:
            # 清理玩家狀態
            if player_id:
                self.handle_player_disconnect(player_id)
            client_socket.close()
            print(f"[大廳伺服器] 連線關閉: {addr}")
    
    def handle_register(self, message):
        """處理註冊請求"""
        username = message.get("username")
        password = message.get("password")
        
        if not username or not password:
            return {"success": False, "message": "帳號或密碼不能為空"}
        
        success, msg = self.db.register_player(username, password)
        return {"success": success, "message": msg}
    
    def handle_login(self, message, client_socket):
        """處理登入請求"""
        username = message.get("username")
        password = message.get("password")
        
        if not username or not password:
            return {"success": False, "message": "帳號或密碼不能為空"}
        
        success, result = self.db.login_player(username, password)
        if success:
            with self.lock:
                # 防止同帳號重複登入
                if result["id"] in self.online_players:
                    return {"success": False, "message": "該帳號已在線上，請先登出後再登入"}
                self.online_players[result["id"]] = {
                    "socket": client_socket,
                    "username": result["username"]
                }
            return {"success": True, "player": result}
        else:
            return {"success": False, "message": result}
    
    def handle_list_games(self):
        """列出所有可用遊戲"""
        games = self.db.get_active_games()
        return {"success": True, "games": games}
    
    def handle_get_game_detail(self, message):
        """獲取遊戲詳細資訊"""
        game_id = message.get("game_id")
        if not game_id:
            return {"success": False, "message": "缺少遊戲ID"}
        
        game_info = self.db.get_game_by_id(game_id)
        if not game_info:
            return {"success": False, "message": "遊戲不存在"}
        
        ratings = self.db.get_game_ratings(game_id)
        return {"success": True, "game": game_info, "ratings": ratings}
    
    def handle_download_game(self, message, player_id):
        """處理遊戲下載"""
        if not player_id:
            return {"success": False, "message": "請先登入"}
        
        game_id = message.get("game_id")
        if not game_id:
            return {"success": False, "message": "缺少遊戲ID"}
        
        game_info = self.db.get_game_by_id(game_id)
        if not game_info or not game_info["is_active"]:
            return {"success": False, "message": "遊戲不存在或已下架"}
        
        try:
            # 讀取遊戲檔案
            game_dir = f"uploaded_games/{game_info['name']}/{game_info['version']}"
            
            if not os.path.exists(game_dir):
                return {"success": False, "message": "遊戲檔案不存在"}
            
            files = []
            for root, dirs, filenames in os.walk(game_dir):
                for filename in filenames:
                    file_path = os.path.join(root, filename)
                    relative_path = os.path.relpath(file_path, game_dir)
                    
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    files.append({
                        "name": relative_path,
                        "content": content
                    })
            
            # 記錄下載
            self.db.record_download(player_id, game_id, game_info["version"])
            
            return {
                "success": True,
                "game_info": game_info,
                "files": files
            }
            
        except Exception as e:
            return {"success": False, "message": f"下載失敗: {str(e)}"}
    
    def handle_create_room(self, message, player_id):
        """建立房間"""
        if not player_id:
            return {"success": False, "message": "請先登入"}
        
        game_id = message.get("game_id")
        if not game_id:
            return {"success": False, "message": "缺少遊戲ID"}
        
        game_info = self.db.get_game_by_id(game_id)
        if not game_info or not game_info["is_active"]:
            return {"success": False, "message": "遊戲不存在或已下架"}
        
        with self.lock:
            # 檢查玩家是否已在房間中
            if player_id in self.player_rooms:
                return {"success": False, "message": "你已經在一個房間中"}
            
            room_id = self.next_room_id
            self.next_room_id += 1
            
            player_info = self.online_players.get(player_id)
            if not player_info:
                return {"success": False, "message": "玩家資訊不存在"}
            
            room = Room(room_id, game_id, game_info, {
                "id": player_id,
                "username": player_info["username"]
            })
            
            self.rooms[room_id] = room
            self.player_rooms[player_id] = room_id
        
        print(f"[大廳伺服器] 房間 {room_id} 建立成功 (遊戲: {game_info['name']})")
        return {"success": True, "room": room.to_dict()}
    
    def handle_list_rooms(self):
        """列出所有房間"""
        with self.lock:
            rooms = [room.to_dict() for room in self.rooms.values() if room.status == "waiting"]
        return {"success": True, "rooms": rooms}
    
    def handle_join_room(self, message, player_id):
        """加入房間"""
        if not player_id:
            return {"success": False, "message": "請先登入"}
        
        room_id = message.get("room_id")
        if not room_id:
            return {"success": False, "message": "缺少房間ID"}
        
        with self.lock:
            if player_id in self.player_rooms:
                return {"success": False, "message": "你已經在一個房間中"}
            
            room = self.rooms.get(room_id)
            if not room:
                return {"success": False, "message": "房間不存在"}
            
            if room.status != "waiting":
                return {"success": False, "message": "房間已開始遊戲"}
            
            if room.is_full():
                return {"success": False, "message": "房間已滿"}
            
            player_info = self.online_players.get(player_id)
            if not player_info:
                return {"success": False, "message": "玩家資訊不存在"}
            
            room.add_player({
                "id": player_id,
                "username": player_info["username"]
            })
            self.player_rooms[player_id] = room_id
            
            # 廣播更新
            self.broadcast_to_room(room_id, {
                "type": "room_update",
                "room": room.to_dict()
            }, exclude_player_id=player_id)
        
        print(f"[大廳伺服器] 玩家 {player_info['username']} 加入房間 {room_id}")
        return {"success": True, "room": room.to_dict()}
    
    def handle_leave_room(self, player_id):
        """離開房間"""
        if not player_id:
            return {"success": False, "message": "請先登入"}
        
        with self.lock:
            room_id = self.player_rooms.get(player_id)
            if not room_id:
                return {"success": False, "message": "你不在任何房間中"}
            
            room = self.rooms.get(room_id)
            if not room:
                return {"success": False, "message": "房間不存在"}
            
            is_host = (room.host_player["id"] == player_id)
            room.remove_player(player_id)
            del self.player_rooms[player_id]
            
            # 如果房間沒人了，刪除房間
            if len(room.players) == 0:
                # 確保遊戲伺服器進程已終止
                if room.game_server_process:
                    try:
                        print(f"[大廳伺服器] 正在終止房間 {room_id} 的遊戲伺服器 (PID: {room.game_server_process.pid})...")
                        room.game_server_process.terminate()
                        room.game_server_process.wait(timeout=5)
                    except Exception as e:
                        print(f"[大廳伺服器] 終止遊戲伺服器失敗: {e}")
                        try:
                            room.game_server_process.kill()
                        except:
                            pass
                
                del self.rooms[room_id]
                print(f"[大廳伺服器] 房間 {room_id} 已關閉（無玩家）")
                return {"success": True, "message": "已離開房間"}
            
            # 如果離開的是房主，轉移房主給第一個玩家
            if is_host and len(room.players) > 0:
                room.host_player = room.players[0]
                print(f"[大廳伺服器] 房間 {room_id} 房主轉移給 {room.host_player['username']}")
                
                # 廣播更新
                self.broadcast_to_room(room_id, {
                    "type": "room_update",
                    "room": room.to_dict()
                }, exclude_player_id=player_id)
                
                return {"success": True, "message": "已離開房間", "new_host": room.host_player['username']}
            
            # 廣播更新
            self.broadcast_to_room(room_id, {
                "type": "room_update",
                "room": room.to_dict()
            }, exclude_player_id=player_id)
        
        return {"success": True, "message": "已離開房間"}
    
    def handle_start_game(self, player_id):
        """開始遊戲"""
        if not player_id:
            return {"success": False, "message": "請先登入"}
        
        with self.lock:
            room_id = self.player_rooms.get(player_id)
            if not room_id:
                return {"success": False, "message": "你不在任何房間中"}
            
            room = self.rooms.get(room_id)
            if not room:
                return {"success": False, "message": "房間不存在"}
            
            if room.host_player["id"] != player_id:
                return {"success": False, "message": "只有房主可以開始遊戲"}
            
            if not room.can_start():
                return {"success": False, "message": f"人數不足，至少需要 {room.game_info['min_players']} 人"}
            
            room.status = "playing"
        
        # 啟動遊戲伺服器
        game_server_info = self.start_game_server(room)
        
        # 廣播遊戲開始
        self.broadcast_to_room(room_id, {
            "type": "game_started",
            "server_info": game_server_info
        }, exclude_player_id=player_id)
        
        return {
            "success": True,
            "message": "遊戲伺服器已啟動",
            "server_info": game_server_info
        }
    
    def handle_get_room_status(self, player_id):
        """獲取房間狀態"""
        if not player_id:
            return {"success": False, "message": "請先登入"}
        
        with self.lock:
            room_id = self.player_rooms.get(player_id)
            if not room_id:
                return {"success": False, "message": "你不在任何房間中"}
            
            room = self.rooms.get(room_id)
            if not room:
                return {"success": False, "message": "房間不存在"}
            
            response = {
                "success": True,
                "room": room.to_dict(),
                "status": room.status
            }
            
            # 如果遊戲已開始，返回伺服器資訊
            if room.status == "playing":
                response["server_info"] = {
                    "host": self.get_host_ip(),
                    "port": room.server_port,
                    "game_name": room.game_info["name"],
                    "game_type": room.game_info["type"]
                }
            
            return response
    
    def get_host_ip(self):
        """取得本機 IP"""
        if self.host != '0.0.0.0':
            return self.host
        try:
            # 建立一個 UDP socket 連線到外部 IP (不會真的發送封包)
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(('8.8.8.8', 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return '127.0.0.1'

    def get_free_port(self):
        """取得可用埠口"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('', 0))
                s.listen(1)
                port = s.getsockname()[1]
            return port
        except:
            return 0

    def start_game_server(self, room):
        """啟動遊戲伺服器"""
        game_info = room.game_info
        game_dir = os.path.abspath(f"uploaded_games/{game_info['name']}/{game_info['version']}")
        server_file_name = game_info.get("server_file", "game_server.py")
        
        # 動態分配埠口
        port = self.get_free_port()
        if port == 0:
            # 如果動態分配失敗，回退到設定檔的埠口（可能會衝突）
            port = game_info["server_port"]
            print(f"[大廳伺服器] 警告：無法動態分配埠口，使用預設埠口 {port}")
        
        try:
            process = subprocess.Popen(
                [sys.executable, server_file_name, str(port)],
                cwd=game_dir
            )
            room.game_server_process = process
            room.server_port = port
            print(f"[大廳伺服器] 遊戲伺服器已啟動 (PID: {process.pid}, Port: {port})")
            
            # 取得正確的 IP 地址
            host_ip = self.get_host_ip()
            
            return {
                "host": host_ip,
                "port": port,
                "game_name": game_info["name"],
                "game_type": game_info["type"]
            }
        except Exception as e:
            print(f"[大廳伺服器] 啟動遊戲伺服器失敗: {e}")
            return None
    
    def handle_add_rating(self, message, player_id):
        """處理評分"""
        if not player_id:
            return {"success": False, "message": "請先登入"}
        
        game_id = message.get("game_id")
        rating = message.get("rating")
        comment = message.get("comment", "")
        
        if not game_id or not rating:
            return {"success": False, "message": "缺少必要參數"}
        
        success, msg = self.db.add_rating(game_id, player_id, rating, comment)
        return {"success": success, "message": msg}
    
    def handle_get_ratings(self, message):
        """獲取評分"""
        game_id = message.get("game_id")
        if not game_id:
            return {"success": False, "message": "缺少遊戲ID"}
        
        ratings = self.db.get_game_ratings(game_id)
        return {"success": True, "ratings": ratings}
    
    def handle_player_disconnect(self, player_id):
        """處理玩家斷線"""
        with self.lock:
            # 從線上列表移除
            if player_id in self.online_players:
                del self.online_players[player_id]
            
            # 離開房間
            if player_id in self.player_rooms:
                room_id = self.player_rooms[player_id]
                room = self.rooms.get(room_id)
                if room:
                    is_host = (room.host_player["id"] == player_id)
                    room.remove_player(player_id)
                    
                    if len(room.players) == 0:
                        # 確保遊戲伺服器進程已終止
                        if room.game_server_process:
                            try:
                                print(f"[大廳伺服器] 正在終止房間 {room_id} 的遊戲伺服器 (PID: {room.game_server_process.pid})...")
                                room.game_server_process.terminate()
                                room.game_server_process.wait(timeout=5)
                            except Exception as e:
                                print(f"[大廳伺服器] 終止遊戲伺服器失敗: {e}")
                                try:
                                    room.game_server_process.kill()
                                except:
                                    pass
                        del self.rooms[room_id]
                    else:
                        if is_host:
                            room.host_player = room.players[0]
                        
                        # 廣播更新
                        self.broadcast_to_room(room_id, {
                            "type": "room_update",
                            "room": room.to_dict()
                        })
                        
                del self.player_rooms[player_id]
    
    def stop(self):
        """停止伺服器"""
        self.running = False
        if self.server_socket:
            self.server_socket.close()

if __name__ == "__main__":
    host = sys.argv[1] if len(sys.argv) > 1 else '0.0.0.0'
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 6002
    
    server = LobbyServer(host, port)
    try:
        server.start()
    except KeyboardInterrupt:
        print("\n[大廳伺服器] 正在關閉...")
        server.stop()
