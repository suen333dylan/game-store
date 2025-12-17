#!/usr/bin/env python3
"""
猜數字對戰遊戲伺服器 (GUI 雙人遊戲)
每位玩家設定一個 1-100 的數字，然後互相猜對方的數字
"""
import socket
import json
import sys

class NumberGuessServer:
    def __init__(self, port):
        self.port = port
        self.clients = []
        self.player_numbers = [None, None]  # 每位玩家設定的數字
        self.player_guesses = [0, 0]  # 每位玩家的猜測次數
        self.server_socket = None
        
    def start(self):
        """啟動遊戲伺服器"""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind(('0.0.0.0', self.port))
        self.server_socket.listen(2)
        print(f"[猜數字對戰伺服器] 在埠口 {self.port} 上啟動")
        
        # 等待兩位玩家連線
        for i in range(2):
            client_socket, addr = self.server_socket.accept()
            self.clients.append(client_socket)
            print(f"[猜數字對戰伺服器] 玩家 {i+1} 已連線")
            client_socket.sendall(json.dumps({
                "type": "connected",
                "player_id": i
            }).encode())
        
        print("[猜數字對戰伺服器] 遊戲開始！")
        self.run_game()
        
    def run_game(self):
        """執行遊戲邏輯"""
        # 階段1：等待雙方設定數字
        print("[猜數字對戰伺服器] 等待玩家設定數字...")
        for i in range(2):
            self.clients[i].sendall(json.dumps({
                "type": "set_number",
                "message": "請設定你的數字 (1-100)"
            }).encode())
            
            data = self.clients[i].recv(4096).decode()
            if not data:
                print(f"[猜數字對戰伺服器] 玩家 {i+1} 斷開連線")
                return
                
            try:
                message = json.loads(data)
            except json.JSONDecodeError:
                print(f"[錯誤] JSON 解析失敗: {data}")
                return
                
            if message["type"] == "number_set":
                self.player_numbers[i] = message["number"]
                print(f"[猜數字對戰伺服器] 玩家 {i+1} 已設定數字")
        
        # 階段2：開始猜測
        print("[猜數字對戰伺服器] 開始猜測階段！")
        self.broadcast({
            "type": "start_guessing",
            "message": "雙方已設定完成，開始猜測！"
        })
        
        game_over = False
        current_player = 0
        
        while not game_over:
            # 通知當前玩家輪到他猜
            self.clients[current_player].sendall(json.dumps({
                "type": "your_turn",
                "guesses": self.player_guesses[current_player]
            }).encode())
            
            # 通知另一位玩家等待
            other_player = 1 - current_player
            self.clients[other_player].sendall(json.dumps({
                "type": "wait",
                "message": "等待對手猜測..."
            }).encode())
            
            try:
                # 接收猜測
                data = self.clients[current_player].recv(4096).decode()
                if not data:
                    print(f"[猜數字對戰伺服器] 玩家 {current_player} 斷開連線")
                    break
                    
                try:
                    message = json.loads(data)
                except json.JSONDecodeError:
                    print(f"[錯誤] JSON 解析失敗: {data}")
                    continue
                
                if message["type"] == "guess":
                    guess = message["number"]
                    self.player_guesses[current_player] += 1
                    target = self.player_numbers[other_player]
                    
                    if guess == target:
                        # 猜中了！
                        self.broadcast({
                            "type": "game_over",
                            "winner": current_player,
                            "target_numbers": self.player_numbers,
                            "guesses": self.player_guesses
                        })
                        game_over = True
                    elif guess < target:
                        self.clients[current_player].sendall(json.dumps({
                            "type": "hint",
                            "hint": "too_low",
                            "message": "太小了！"
                        }).encode())
                    else:
                        self.clients[current_player].sendall(json.dumps({
                            "type": "hint",
                            "hint": "too_high",
                            "message": "太大了！"
                        }).encode())
                    
                    # 切換玩家
                    if not game_over:
                        current_player = 1 - current_player
                        
            except Exception as e:
                print(f"[錯誤] {e}")
                game_over = True
        
        print("[猜數字對戰伺服器] 遊戲結束")
        self.close()
        
    def broadcast(self, message):
        """廣播訊息給所有玩家"""
        data = json.dumps(message).encode()
        for client in self.clients:
            try:
                client.sendall(data)
            except:
                pass
                
    def close(self):
        """關閉伺服器"""
        for client in self.clients:
            try:
                client.close()
            except:
                pass
        if self.server_socket:
            self.server_socket.close()

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5002
    server = NumberGuessServer(port)
    try:
        server.start()
    except KeyboardInterrupt:
        print("\n[猜數字對戰伺服器] 正在關閉...")
    finally:
        server.close()
