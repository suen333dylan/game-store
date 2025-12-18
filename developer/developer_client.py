#!/usr/bin/env python3
"""
開發者客戶端
提供選單式介面讓開發者上傳、更新、下架遊戲
"""
import socket
import json
import os
import sys

class DeveloperClient:
    def __init__(self, server_host='localhost', server_port=6001):
        self.server_host = server_host
        self.server_port = server_port
        self.socket = None
        self.developer = None
        
    def connect(self):
        """連線到開發者伺服器"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.server_host, self.server_port))
            return True
        except Exception as e:
            print(f"❌ 連線失敗: {e}")
            return False
    
    def send_message(self, message):
        """發送訊息給伺服器"""
        try:
            # 發送數據
            data_to_send = json.dumps(message).encode('utf-8')
            self.socket.sendall(data_to_send)
            
            # 接收回應（支援大數據）
            chunks = []
            while True:
                chunk = self.socket.recv(65536).decode('utf-8')
                if not chunk:
                    break
                chunks.append(chunk)
                try:
                    response = json.loads(''.join(chunks))
                    return response
                except json.JSONDecodeError:
                    continue
        except Exception as e:
            print(f"❌ 通訊錯誤: {e}")
            return {"success": False, "message": str(e)}
    
    def register(self):
        """註冊開發者帳號"""
        print("\n========== 註冊開發者帳號 ==========")
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
        print("\n========== 開發者登入 ==========")
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
            self.developer = response["developer"]
            print(f"✅ 歡迎回來，{self.developer['username']}！")
            return True
        else:
            print(f"❌ {response['message']}")
            return False
    
    def read_game_files(self, game_dir):
        """讀取遊戲目錄中的所有檔案"""
        files = []
        for root, dirs, filenames in os.walk(game_dir):
            # 忽略 __pycache__ 等目錄
            dirs[:] = [d for d in dirs if not d.startswith('__')]
            
            for filename in filenames:
                if filename.endswith('.pyc'):
                    continue
                    
                file_path = os.path.join(root, filename)
                relative_path = os.path.relpath(file_path, game_dir)
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    files.append({
                        "name": relative_path,
                        "content": content
                    })
                except Exception as e:
                    print(f"⚠️  無法讀取檔案 {relative_path}: {e}")
        
        return files
    
    def upload_game(self):
        """上傳遊戲"""
        print("\n========== 上傳新遊戲 ==========")
        
        # 列出 games 目錄中的遊戲
        games_dir = "games"
        if not os.path.exists(games_dir):
            print(f"❌ 遊戲目錄不存在: {games_dir}")
            return
        
        game_folders = [d for d in os.listdir(games_dir) 
                       if os.path.isdir(os.path.join(games_dir, d))]
        
        if not game_folders:
            print("❌ 沒有可上傳的遊戲")
            return
        
        print("\n可用的遊戲：")
        for i, folder in enumerate(game_folders, 1):
            print(f"  {i}. {folder}")
        
        try:
            choice = int(input("\n請選擇要上傳的遊戲 (輸入編號): "))
            if 1 <= choice <= len(game_folders):
                game_folder = game_folders[choice - 1]
            else:
                print("❌ 無效的選擇")
                return
        except ValueError:
            print("❌ 請輸入有效的數字")
            return
        
        game_dir = os.path.join(games_dir, game_folder)
        config_file = os.path.join(game_dir, "game_config.json")
        
        if not os.path.exists(config_file):
            print(f"❌ 找不到遊戲配置檔: {config_file}")
            return
        
        # 讀取遊戲配置
        with open(config_file, 'r', encoding='utf-8') as f:
            game_config = json.load(f)
        
        print(f"\n遊戲名稱: {game_config['game_name']}")
        print(f"版本: {game_config['version']}")
        print(f"描述: {game_config['description']}")
        
        confirm = input("\n確認上傳？ (y/n): ").strip().lower()
        if confirm != 'y':
            print("❌ 已取消")
            return
        
        # 讀取所有遊戲檔案
        print("正在讀取遊戲檔案...")
        files = self.read_game_files(game_dir)
        print(f"共讀取 {len(files)} 個檔案")
        
        # 發送上傳請求
        print("正在上傳...")
        response = self.send_message({
            "type": "upload_game",
            "game_config": game_config,
            "files": files
        })
        
        if response["success"]:
            print(f"✅ {response['message']}")
        else:
            print(f"❌ {response['message']}")
    
    def update_game(self):
        """更新遊戲"""
        print("\n========== 更新遊戲版本 ==========")
        
        # 獲取我的遊戲列表
        response = self.send_message({"type": "list_my_games"})
        
        if not response["success"]:
            print(f"❌ {response['message']}")
            return
        
        games = response["games"]
        if not games:
            print("你還沒有上傳任何遊戲")
            return
        
        print("\n你的遊戲：")
        for i, game in enumerate(games, 1):
            status = "✅ 上架中" if game["is_active"] else "❌ 已下架"
            print(f"  {i}. {game['name']} (版本: {game['version']}) - {status}")
        
        try:
            choice = int(input("\n請選擇要更新的遊戲 (輸入編號): "))
            if 1 <= choice <= len(games):
                game = games[choice - 1]
            else:
                print("❌ 無效的選擇")
                return
        except ValueError:
            print("❌ 請輸入有效的數字")
            return
        
        # 輸入新版本號
        # new_version = input(f"請輸入新版本號 (當前: {game['version']}): ").strip()
        # if not new_version:
        #     print("❌ 版本號不能為空")
        #     return
        
        # 選擇遊戲檔案
        games_dir = "games"
        game_folders = [d for d in os.listdir(games_dir) 
                       if os.path.isdir(os.path.join(games_dir, d))]
        
        print("\n可用的遊戲資料夾：")
        for i, folder in enumerate(game_folders, 1):
            print(f"  {i}. {folder}")
        
        try:
            folder_choice = int(input("\n請選擇遊戲資料夾 (輸入編號): "))
            if 1 <= folder_choice <= len(game_folders):
                game_folder = game_folders[folder_choice - 1]
            else:
                print("❌ 無效的選擇")
                return
        except ValueError:
            print("❌ 請輸入有效的數字")
            return
        
        game_dir = os.path.join(games_dir, game_folder)
        config_file = os.path.join(game_dir, "game_config.json")
        
        if not os.path.exists(config_file):
            print(f"❌ 找不到遊戲配置檔: {config_file}")
            return
            
        # 從配置檔讀取新版本號
        with open(config_file, 'r', encoding='utf-8') as f:
            game_config = json.load(f)
            new_version = game_config.get("version")
            
        if not new_version:
            print("❌ 配置檔中缺少版本號")
            return
            
        if new_version == game['version']:
            print(f"⚠️  警告：新版本號 ({new_version}) 與當前版本相同")
            print("請先修改 game_config.json 中的版本號再更新")
            return

        # 讀取遊戲檔案
        print("正在讀取遊戲檔案...")
        files = self.read_game_files(game_dir)
        print(f"共讀取 {len(files)} 個檔案")
        
        confirm = input(f"\n確認更新 {game['name']} 到版本 {new_version}？ (y/n): ").strip().lower()
        if confirm != 'y':
            print("❌ 已取消")
            return
        
        # 發送更新請求
        print("正在更新...")
        response = self.send_message({
            "type": "update_game",
            "game_id": game["id"],
            "new_version": new_version,
            "files": files
        })
        
        if response["success"]:
            print(f"✅ {response['message']}")
        else:
            print(f"❌ {response['message']}")
    
    def deactivate_game(self):
        """下架遊戲"""
        print("\n========== 下架遊戲 ==========")
        
        # 獲取我的遊戲列表
        response = self.send_message({"type": "list_my_games"})
        
        if not response["success"]:
            print(f"❌ {response['message']}")
            return
        
        games = [g for g in response["games"] if g["is_active"]]
        if not games:
            print("你沒有上架中的遊戲")
            return
        
        print("\n上架中的遊戲：")
        for i, game in enumerate(games, 1):
            print(f"  {i}. {game['name']} (版本: {game['version']})")
        
        try:
            choice = int(input("\n請選擇要下架的遊戲 (輸入編號): "))
            if 1 <= choice <= len(games):
                game = games[choice - 1]
            else:
                print("❌ 無效的選擇")
                return
        except ValueError:
            print("❌ 請輸入有效的數字")
            return
        
        confirm = input(f"\n確認下架 {game['name']}？ (y/n): ").strip().lower()
        if confirm != 'y':
            print("❌ 已取消")
            return
        
        response = self.send_message({
            "type": "deactivate_game",
            "game_id": game["id"]
        })
        
        if response["success"]:
            print(f"✅ {response['message']}")
        else:
            print(f"❌ {response['message']}")
    
    def list_my_games(self):
        """列出我的遊戲"""
        print("\n========== 我的遊戲 ==========")
        
        response = self.send_message({"type": "list_my_games"})
        
        if not response["success"]:
            print(f"❌ {response['message']}")
            return
        
        games = response["games"]
        if not games:
            print("你還沒有上傳任何遊戲")
            return
        
        for game in games:
            status = "✅ 上架中" if game["is_active"] else "❌ 已下架"
            print(f"\n遊戲名稱: {game['name']}")
            print(f"  當前版本: {game['version']}")
            print(f"  類型: {game['type']}")
            print(f"  玩家數: {game['min_players']}-{game['max_players']}")
            print(f"  狀態: {status}")
            print(f"  建立時間: {game['created_at']}")
    
    def main_menu(self):
        """主選單"""
        while True:
            print("\n" + "="*50)
            print("          開發者平台主選單")
            print("="*50)
            if self.developer:
                print(f"  登入身分: {self.developer['username']}")
            print("\n  1. 上傳新遊戲")
            print("  2. 更新遊戲版本")
            print("  3. 下架遊戲")
            print("  4. 查看我的遊戲")
            print("  5. 登出")
            print("  6. 離開")
            print("="*50)
            
            choice = input("\n請選擇功能 (1-6): ").strip()
            
            if choice == '1':
                self.upload_game()
            elif choice == '2':
                self.update_game()
            elif choice == '3':
                self.deactivate_game()
            elif choice == '4':
                self.list_my_games()
            elif choice == '5':
                self.developer = None
                print("✅ 已登出")
                break
            elif choice == '6':
                print("👋 再見！")
                return False
            else:
                print("❌ 無效的選擇，請重試")
            
            input("\n按 Enter 繼續...")
        
        return True
    
    def run(self):
        """執行客戶端"""
        print("\n" + "="*50)
        print("        🎮 遊戲商城 - 開發者平台 🎮")
        print("="*50)
        
        if not self.connect():
            return
        
        try:
            while True:
                if not self.developer:
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
    server_port = int(sys.argv[2]) if len(sys.argv) > 2 else 6001
    
    client = DeveloperClient(server_host, server_port)
    client.run()
