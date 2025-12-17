#!/usr/bin/env python3
"""
玩家/大廳客戶端
提供選單式介面讓玩家瀏覽遊戲、下載、建立房間、遊玩遊戲
"""
import socket
import json
import os
import sys
import subprocess
import time
import errno
import select

class LobbyClient:
    def __init__(self, server_host='localhost', server_port=6002):
        self.server_host = server_host
        self.server_port = server_port
        self.socket = None
        self.player = None
        self.downloads_dir = "downloads"
        self.current_room = None
        
    def connect(self):
        """連線到大廳伺服器"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.server_host, self.server_port))
            return True
        except Exception as e:
            print(f"❌ 連線失敗: {e}")
            return False

    def wait_for_port(self, host, port, timeout=5.0, interval=0.25):
        """等待遊戲伺服器埠口開啟，避免客戶端過早連線"""
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                with socket.create_connection((host, port), timeout=1):
                    return True
            except OSError as e:
                if e.errno not in (errno.ECONNREFUSED, errno.ETIMEDOUT):
                    return False
            time.sleep(interval)
        return False
    
    def send_message(self, message):
        """發送訊息給伺服器"""
        try:
            # 發送數據
            data_to_send = json.dumps(message).encode('utf-8')
            self.socket.sendall(data_to_send)
            
            # 接收回應
            while True:
                response = self.receive_one_json()
                if not response:
                    return {"success": False, "message": "連線中斷"}
                
                # 檢查是否為事件通知
                if response.get("type") in ["room_update", "game_started"]:
                    self.handle_event(response)
                    continue
                
                return response
        except Exception as e:
            print(f"❌ 通訊錯誤: {e}")
            return {"success": False, "message": str(e)}

    def receive_one_json(self):
        """接收一個完整的 JSON 物件"""
        chunks = []
        while True:
            try:
                chunk = self.socket.recv(65536).decode('utf-8')
                if not chunk:
                    return None
                chunks.append(chunk)
                try:
                    return json.loads(''.join(chunks))
                except json.JSONDecodeError:
                    continue
            except Exception:
                return None

    def handle_event(self, event):
        """處理伺服器推送的事件"""
        if event["type"] == "room_update":
            self.current_room = event["room"]
            # 若在 send_message 等待過程中收到更新，簡單提示即可
            # 實際 UI 更新由 room_menu 的 select 迴圈處理
            pass
            
        elif event["type"] == "game_started":
            # 這裡通常不會觸發，因為 game_started 主要在 room_menu 等待時收到
            pass
    
    def register(self):
        """註冊玩家帳號"""
        print("\n========== 註冊玩家帳號 ==========")
        username = input("請輸入帳號: ").strip()
        password = input("請輸入密碼: ").strip()
        
        if not username or not password:
            print("❌ 帳號或密碼不能為空")
            return False
        
        response = self.send_message({
            "type": "register",
            "username": username,
            "password": password
        })
        
        if response["success"]:
            print(f"✅ {response['message']}")
            return True
        else:
            print(f"❌ {response['message']}")
            return False
    
    def login(self):
        """登入"""
        print("\n========== 玩家登入 ==========")
        username = input("請輸入帳號: ").strip()
        password = input("請輸入密碼: ").strip()
        
        if not username or not password:
            print("❌ 帳號或密碼不能為空")
            return False
        
        response = self.send_message({
            "type": "login",
            "username": username,
            "password": password
        })
        
        if response["success"]:
            self.player = response["player"]
            # 建立玩家的下載目錄
            self.downloads_dir = f"downloads/{self.player['username']}"
            os.makedirs(self.downloads_dir, exist_ok=True)
            print(f"✅ 歡迎回來，{self.player['username']}！")
            return True
        else:
            print(f"❌ {response['message']}")
            return False
    
    def list_games(self):
        """瀏覽遊戲商城"""
        print("\n========== 遊戲商城 ==========")
        
        response = self.send_message({"type": "list_games"})
        
        if not response["success"]:
            print(f"❌ {response['message']}")
            return None
        
        games = response["games"]
        if not games:
            print("目前沒有可遊玩的遊戲")
            return None
        
        print("\n可用遊戲：")
        for i, game in enumerate(games, 1):
            print(f"\n  {i}. 【{game['name']}】")
            print(f"     作者: {game['author']}")
            print(f"     版本: {game['version']}")
            print(f"     類型: {game['type'].upper()}")
            print(f"     玩家數: {game['min_players']}-{game['max_players']}")
            print(f"     評分: {'⭐' * int(game['avg_rating'])} ({game['avg_rating']}/5.0, {game['rating_count']} 人評分)")
            print(f"     簡介: {game['description']}")
        
        return games
    
    def view_game_detail(self, games):
        """查看遊戲詳細資訊"""
        if not games:
            games = self.list_games()
            if not games:
                return
        
        try:
            choice = int(input("\n請輸入遊戲編號查看詳細資訊 (0返回): "))
            if choice == 0:
                return
            if 1 <= choice <= len(games):
                game = games[choice - 1]
            else:
                print("❌ 無效的選擇")
                return
        except ValueError:
            print("❌ 請輸入有效的數字")
            return
        
        response = self.send_message({
            "type": "get_game_detail",
            "game_id": game["id"]
        })
        
        if not response["success"]:
            print(f"❌ {response['message']}")
            return
        
        game_info = response["game"]
        ratings = response["ratings"]
        
        print(f"\n{'='*60}")
        print(f"  遊戲名稱: {game_info['name']}")
        print(f"  作者: {game_info['author']}")
        print(f"  版本: {game_info['version']}")
        print(f"  類型: {game_info['type'].upper()}")
        print(f"  玩家數: {game_info['min_players']}-{game_info['max_players']}")
        print(f"  伺服器埠口: {game_info['server_port']}")
        print(f"  簡介: {game_info['description']}")
        print(f"{'='*60}")
        
        if ratings:
            print(f"\n最近評論：")
            for rating in ratings[:5]:
                stars = '⭐' * rating['rating']
                print(f"\n  {rating['player']} - {stars} ({rating['rating']}/5)")
                if rating['comment']:
                    print(f"  「{rating['comment']}」")
                print(f"  {rating['date']}")
        else:
            print("\n尚無評論")
    
    def download_game(self):
        """下載遊戲"""
        print("\n========== 下載遊戲 ==========")
        
        games = self.list_games()
        if not games:
            return
        
        try:
            choice = int(input("\n請選擇要下載的遊戲 (輸入編號, 0返回): "))
            if choice == 0:
                return
            if 1 <= choice <= len(games):
                game = games[choice - 1]
            else:
                print("❌ 無效的選擇")
                return
        except ValueError:
            print("❌ 請輸入有效的數字")
            return
        
        # 檢查是否已下載
        game_dir = os.path.join(self.downloads_dir, game['name'])
        if os.path.exists(game_dir):
            print(f"\n⚠️  你已經下載過這個遊戲")
            print(f"   目前版本: {game['version']}")
            update = input("是否要更新到最新版本？ (y/n): ").strip().lower()
            if update != 'y':
                return
        
        print(f"\n正在下載 {game['name']}...")
        response = self.send_message({
            "type": "download_game",
            "game_id": game["id"]
        })
        
        if not response["success"]:
            print(f"❌ {response['message']}")
            return
        
        # 儲存遊戲檔案
        game_info = response["game_info"]
        files = response["files"]
        
        # 建立遊戲目錄
        game_dir = os.path.join(self.downloads_dir, game_info['name'])
        os.makedirs(game_dir, exist_ok=True)
        
        # 寫入檔案
        for file_info in files:
            file_path = os.path.join(game_dir, file_info["name"])
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(file_info["content"])
        
        print(f"✅ 下載完成！遊戲已儲存至 {game_dir}")
        print(f"   版本: {game_info['version']}")
    
    def check_and_download_game(self, game_name, game_id, server_version):
        """檢查並下載/更新遊戲"""
        game_dir = os.path.join(self.downloads_dir, game_name)
        
        # 檢查是否已下載
        if os.path.exists(game_dir):
            # 檢查版本
            try:
                config_file = os.path.join(game_dir, "game_config.json")
                if os.path.exists(config_file):
                    with open(config_file, 'r', encoding='utf-8') as f:
                        config = json.load(f)
                        local_version = config.get("version", "0.0.0")
                        
                    if local_version == server_version:
                        return True
                    
                    print(f"\n⚠️  發現新版本！ (本地: {local_version}, 伺服器: {server_version})")
                    update = input("是否更新？ (y/n): ").strip().lower()
                    if update != 'y':
                        return False
                else:
                    # 配置檔遺失，視為未下載
                    pass
            except Exception:
                pass
        else:
            print(f"\n⚠️  你還沒有下載這個遊戲")
            download = input("是否現在下載？ (y/n): ").strip().lower()
            if download != 'y':
                return False
        
        # 下載遊戲
        print(f"\n正在下載 {game_name}...")
        response = self.send_message({
            "type": "download_game",
            "game_id": game_id
        })
        
        if not response["success"]:
            print(f"❌ 下載失敗: {response['message']}")
            return False
        
        # 儲存遊戲檔案
        game_info = response["game_info"]
        files = response["files"]
        os.makedirs(game_dir, exist_ok=True)
        
        for file_info in files:
            file_path = os.path.join(game_dir, file_info["name"])
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(file_info["content"])
        
        print(f"✅ 下載完成！")
        return True

    def create_room(self):
        """建立房間"""
        print("\n========== 建立遊戲房間 ==========")
        
        games = self.list_games()
        if not games:
            return
        
        try:
            choice = int(input("\n請選擇要遊玩的遊戲 (輸入編號, 0返回): "))
            if choice == 0:
                return
            if 1 <= choice <= len(games):
                game = games[choice - 1]
            else:
                print("❌ 無效的選擇")
                return
        except ValueError:
            print("❌ 請輸入有效的數字")
            return
        
        # 檢查並下載遊戲
        if not self.check_and_download_game(game['name'], game['id'], game['version']):
            return
        
        # 建立房間
        response = self.send_message({
            "type": "create_room",
            "game_id": game["id"]
        })
        
        if not response["success"]:
            print(f"❌ {response['message']}")
            return
        
        self.current_room = response["room"]
        print(f"\n✅ 房間建立成功！")
        print(f"   房間ID: {self.current_room['room_id']}")
        print(f"   遊戲: {self.current_room['game_name']}")
        print(f"   房主: {self.current_room['host']}")
        print(f"   玩家: {'/'.join(self.current_room['players'])} ({self.current_room['player_count']}/{self.current_room['max_players']})")
        
        # 進入房間等待畫面
        self.room_menu()
    
    def list_rooms(self):
        """列出所有房間"""
        print("\n========== 遊戲房間列表 ==========")
        
        response = self.send_message({"type": "list_rooms"})
        
        if not response["success"]:
            print(f"❌ {response['message']}")
            return None
        
        rooms = response["rooms"]
        if not rooms:
            print("目前沒有可加入的房間")
            return None
        
        print("\n可用房間：")
        for i, room in enumerate(rooms, 1):
            print(f"\n  {i}. 【{room['game_name']}】")
            print(f"     房間ID: {room['room_id']}")
            print(f"     房主: {room['host']}")
            print(f"     玩家: {'/'.join(room['players'])} ({room['player_count']}/{room['max_players']})")
        
        return rooms
    
    def join_room(self):
        """加入房間"""
        print("\n========== 加入遊戲房間 ==========")
        
        rooms = self.list_rooms()
        if not rooms:
            return
        
        try:
            choice = int(input("\n請選擇要加入的房間 (輸入編號, 0返回): "))
            if choice == 0:
                return
            if 1 <= choice <= len(rooms):
                room = rooms[choice - 1]
            else:
                print("❌ 無效的選擇")
                return
        except ValueError:
            print("❌ 請輸入有效的數字")
            return
        
        response = self.send_message({
            "type": "join_room",
            "room_id": room["room_id"]
        })
        
        if not response["success"]:
            print(f"❌ {response['message']}")
            return
        
        self.current_room = response["room"]
        
        # 檢查並下載遊戲 (需要先獲取遊戲版本，這裡先用房間資訊中的遊戲ID去查詢)
        # 為了簡化，我們假設房間資訊中包含了足夠的資訊，或者我們再發一次請求獲取遊戲詳情
        # 但為了效率，我們可以直接嘗試下載，如果版本一致，check_and_download_game 會處理
        
        # 獲取遊戲詳情以得到版本號
        game_detail = self.send_message({
            "type": "get_game_detail",
            "game_id": self.current_room["game_id"]
        })
        
        if game_detail["success"]:
            game_info = game_detail["game"]
            if not self.check_and_download_game(game_info['name'], game_info['id'], game_info['version']):
                # 如果拒絕下載，則離開房間
                self.leave_room()
                return
        
        print(f"\n✅ 已加入房間！")
        print(f"   房間ID: {self.current_room['room_id']}")
        print(f"   遊戲: {self.current_room['game_name']}")
        print(f"   玩家: {'/'.join(self.current_room['players'])} ({self.current_room['player_count']}/{self.current_room['max_players']})")
        
        # 進入房間等待畫面
        self.room_menu()
    
    def room_menu(self):
        """房間選單"""
        self.print_room_status()
        
        while self.current_room:
            # 檢查是否為房主
            is_host = self.current_room['host'] == self.player['username']
            can_start = self.current_room['player_count'] >= self.current_room['min_players']
            
            print("\n請選擇: ", end='', flush=True)
            
            # 使用 select 監聽 socket 和 stdin
            try:
                rlist, _, _ = select.select([self.socket, sys.stdin], [], [])
            except ValueError:
                break
            
            if self.socket in rlist:
                # 收到伺服器訊息
                msg = self.receive_one_json()
                if not msg:
                    print("\n❌ 與伺服器斷線")
                    self.current_room = None
                    break
                
                if msg.get("type") == "room_update":
                    self.current_room = msg["room"]
                    self.print_room_status()
                elif msg.get("type") == "game_started":
                    print("\n✅ 房主已開始遊戲！正在啟動客戶端...")
                    self.launch_game_client(msg["server_info"])
                    break
            
            if sys.stdin in rlist:
                # 使用者輸入
                line = sys.stdin.readline().strip()
                
                if is_host:
                    if can_start:
                        if line == '1':
                            self.start_game()
                            break
                        elif line == '2':
                            self.leave_room()
                            break
                    else:
                        if line == '1':
                            self.leave_room()
                            break
                else:
                    if line == '1':
                        self.leave_room()
                        break

    def print_room_status(self):
        if not self.current_room:
            return
        print(f"\n{'='*50}")
        print(f"  房間: {self.current_room['game_name']} (ID: {self.current_room['room_id']})")
        print(f"  玩家: {'/'.join(self.current_room['players'])} ({self.current_room['player_count']}/{self.current_room['max_players']})")
        print(f"  房主: {self.current_room['host']}")
        print(f"{'='*50}")
        
        is_host = self.current_room['host'] == self.player['username']
        can_start = self.current_room['player_count'] >= self.current_room['min_players']
        
        if is_host:
            if can_start:
                print("\n  1. 開始遊戲")
                print("  2. 離開房間 (將轉移房主)")
            else:
                print("\n  (人數不足，無法開始遊戲)")
                print("  1. 離開房間 (將轉移房主)")
        else:
            print("\n  1. 離開房間")
            print("  (等待房主開始遊戲...)")
    
    def start_game(self):
        """開始遊戲（房主）"""
        response = self.send_message({"type": "start_game"})
        
        if not response["success"]:
            print(f"❌ {response['message']}")
            return
        
        server_info = response["server_info"]
        print(f"\n✅ 遊戲伺服器已啟動！")
        print(f"   伺服器: {server_info['host']}:{server_info['port']}")
        print(f"   遊戲類型: {server_info['game_type'].upper()}")
        
        self.launch_game_client(server_info)
    
    def launch_game_client(self, server_info):
        """啟動遊戲客戶端"""
        print("\n正在啟動遊戲客戶端...")
        print(f"[DEBUG] 伺服器資訊: {server_info}")
        
        game_name = self.current_room['game_name']
        game_dir = os.path.abspath(os.path.join(self.downloads_dir, game_name))
        print(f"[DEBUG] 遊戲目錄: {game_dir}")
        
        # 檢查遊戲是否已下載
        if not os.path.exists(game_dir):
            print(f"❌ 尚未下載遊戲《{game_name}》")
            print("   請先到主選單下載遊戲！")
            return

        if not self.wait_for_port(server_info['host'], server_info['port'], timeout=8.0):
            print("❌ 遊戲伺服器尚未就緒，請稍後重試")
            return
        
        print("[DEBUG] 伺服器埠口已就緒")
        
        # 讀取遊戲配置
        config_file = os.path.join(game_dir, "game_config.json")
        print(f"[DEBUG] 讀取配置檔: {config_file}")
        with open(config_file, 'r', encoding='utf-8') as f:
            game_config = json.load(f)
        
        client_file = os.path.join(game_dir, game_config.get("client_file", "game_client.py"))
        print(f"[DEBUG] 客戶端檔案: {client_file}")
        
        # 處理伺服器主機地址
        # 如果伺服器返回 localhost 或 0.0.0.0，但我們是連線到遠端大廳，則使用大廳的主機地址
        game_host = server_info['host']
        if game_host in ['localhost', '127.0.0.1', '0.0.0.0']:
            if self.server_host not in ['localhost', '127.0.0.1', '0.0.0.0']:
                print(f"[DEBUG] 檢測到本地伺服器地址 {game_host}，替換為大廳地址 {self.server_host}")
                game_host = self.server_host

        try:
            # 啟動遊戲客戶端
            cmd = [sys.executable, client_file, game_host, str(server_info['port'])]
            print(f"[DEBUG] 執行指令: {' '.join(cmd)}")
            print(f"[DEBUG] 工作目錄: {game_dir}")
            
            process = subprocess.run(
                cmd,
                cwd=game_dir,
                capture_output=False,
                text=True
            )
            
            print(f"[DEBUG] 遊戲客戶端退出，返回碼: {process.returncode}")
            print("\n遊戲結束！")
            self.leave_room()
            
        except Exception as e:
            print(f"❌ 啟動遊戲失敗: {e}")
            import traceback
            traceback.print_exc()
    
    def leave_room(self):
        """離開房間"""
        response = self.send_message({"type": "leave_room"})
        
        if response["success"]:
            print("✅ 已離開房間")
        self.current_room = None
    
    def add_rating(self):
        """為遊戲評分"""
        print("\n========== 遊戲評分 ==========")
        
        games = self.list_games()
        if not games:
            return
        
        try:
            choice = int(input("\n請選擇要評分的遊戲 (輸入編號, 0返回): "))
            if choice == 0:
                return
            if 1 <= choice <= len(games):
                game = games[choice - 1]
            else:
                print("❌ 無效的選擇")
                return
        except ValueError:
            print("❌ 請輸入有效的數字")
            return
        
        try:
            rating = int(input(f"\n請為《{game['name']}》評分 (1-5): "))
            if not 1 <= rating <= 5:
                print("❌ 評分必須在 1-5 之間")
                return
        except ValueError:
            print("❌ 請輸入有效的數字")
            return
        
        comment = input("請輸入評論 (可選，直接Enter跳過): ").strip()
        
        response = self.send_message({
            "type": "add_rating",
            "game_id": game["id"],
            "rating": rating,
            "comment": comment
        })
        
        if response["success"]:
            print(f"✅ {response['message']}")
        else:
            print(f"❌ {response['message']}")
    
    def main_menu(self):
        """主選單"""
        while True:
            print("\n" + "="*50)
            print("          遊戲大廳主選單")
            print("="*50)
            if self.player:
                print(f"  登入身分: {self.player['username']}")
            print("\n  1. 瀏覽遊戲商城")
            print("  2. 查看遊戲詳細資訊")
            print("  3. 下載遊戲")
            print("  4. 建立房間")
            print("  5. 加入房間")
            print("  6. 遊戲評分")
            print("  7. 登出")
            print("  8. 離開")
            print("="*50)
            
            choice = input("\n請選擇功能 (1-8): ").strip()
            
            if choice == '1':
                self.list_games()
            elif choice == '2':
                self.view_game_detail(None)
            elif choice == '3':
                self.download_game()
            elif choice == '4':
                self.create_room()
            elif choice == '5':
                self.join_room()
            elif choice == '6':
                self.add_rating()
            elif choice == '7':
                self.player = None
                print("✅ 已登出")
                break
            elif choice == '8':
                print("👋 再見！")
                return False
            else:
                print("❌ 無效的選擇，請重試")
            
            input("\n按 Enter 繼續...")
        
        return True
    
    def run(self):
        """執行客戶端"""
        print("\n" + "="*50)
        print("        🎮 遊戲商城 - 玩家大廳 🎮")
        print("="*50)
        
        if not self.connect():
            return
        
        try:
            while True:
                if not self.player:
                    # 登入/註冊選單
                    print("\n  1. 登入")
                    print("  2. 註冊")
                    print("  3. 離開")
                    
                    choice = input("\n請選擇 (1-3): ").strip()
                    
                    if choice == '1':
                        if self.login():
                            if not self.main_menu():
                                break
                    elif choice == '2':
                        self.register()
                    elif choice == '3':
                        print("👋 再見！")
                        break
                    else:
                        print("❌ 無效的選擇")
                else:
                    if not self.main_menu():
                        break
                        
        except KeyboardInterrupt:
            print("\n\n👋 再見！")
        finally:
            if self.socket:
                self.socket.close()

if __name__ == "__main__":
    server_host = sys.argv[1] if len(sys.argv) > 1 else 'localhost'
    server_port = int(sys.argv[2]) if len(sys.argv) > 2 else 6002
    
    client = LobbyClient(server_host, server_port)
    client.run()
