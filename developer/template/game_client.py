#!/usr/bin/env python3
"""
遊戲客戶端模板
這個檔案是遊戲開發者需要實作的客戶端邏輯
"""
import socket
import json
import sys

class GameClient:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.socket = None
        self.player_id = None
        
    def connect(self):
        """連線到遊戲伺服器"""
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((self.host, self.port))
        
        # 接收連線確認
        data = self.socket.recv(4096).decode()
        message = json.loads(data)
        if message["type"] == "connected":
            self.player_id = message["player_id"]
            print(f"[遊戲客戶端] 成功連線！你是玩家 {self.player_id}")
            return True
        return False
        
    def send_message(self, message):
        """發送訊息給伺服器"""
        try:
            self.socket.send(json.dumps(message).encode())
            return True
        except:
            return False
            
    def receive_message(self):
        """接收來自伺服器的訊息"""
        try:
            data = self.socket.recv(4096).decode()
            return json.loads(data)
        except:
            return None
            
    def play(self):
        """遊戲主邏輯 - 需要被子類別覆寫"""
        raise NotImplementedError("子類別必須實作 play 方法")
        
    def close(self):
        """關閉連線"""
        if self.socket:
            self.socket.close()

if __name__ == "__main__":
    if len(sys.argv) > 2:
        host = sys.argv[1]
        port = int(sys.argv[2])
    else:
        host = "localhost"
        port = 5000
    
    client = GameClient(host, port)
    try:
        if client.connect():
            client.play()
    except KeyboardInterrupt:
        print("\n[遊戲客戶端] 正在離開...")
    finally:
        client.close()
