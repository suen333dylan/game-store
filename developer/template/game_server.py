#!/usr/bin/env python3
"""
遊戲伺服器模板
這個檔案是遊戲開發者需要實作的伺服器端邏輯
"""
import socket
import threading
import json
import sys

class GameServer:
    def __init__(self, port, max_players=2):
        self.port = port
        self.max_players = max_players
        self.clients = []
        self.game_started = False
        self.server_socket = None
        
    def start(self):
        """啟動遊戲伺服器"""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind(('0.0.0.0', self.port))
        self.server_socket.listen(self.max_players)
        print(f"[遊戲伺服器] 在埠口 {self.port} 上啟動，等待玩家連線...")
        
        while len(self.clients) < self.max_players:
            client_socket, addr = self.server_socket.accept()
            self.clients.append(client_socket)
            print(f"[遊戲伺服器] 玩家 {len(self.clients)} 已連線 ({addr})")
            client_socket.send(json.dumps({"type": "connected", "player_id": len(self.clients)}).encode())
        
        print(f"[遊戲伺服器] 所有玩家已就緒，遊戲開始！")
        self.game_started = True
        self.run_game()
        
    def run_game(self):
        """執行遊戲邏輯 - 需要被子類別覆寫"""
        raise NotImplementedError("子類別必須實作 run_game 方法")
        
    def broadcast(self, message):
        """廣播訊息給所有玩家"""
        data = json.dumps(message).encode()
        for client in self.clients:
            try:
                client.send(data)
            except:
                pass
                
    def send_to_player(self, player_id, message):
        """發送訊息給特定玩家"""
        if 0 <= player_id < len(self.clients):
            try:
                self.clients[player_id].send(json.dumps(message).encode())
            except:
                pass
                
    def receive_from_player(self, player_id):
        """接收來自特定玩家的訊息"""
        if 0 <= player_id < len(self.clients):
            try:
                data = self.clients[player_id].recv(4096).decode()
                return json.loads(data)
            except:
                return None
        return None
        
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
    if len(sys.argv) > 1:
        port = int(sys.argv[1])
    else:
        port = 5000
    
    server = GameServer(port)
    try:
        server.start()
    except KeyboardInterrupt:
        print("\n[遊戲伺服器] 正在關閉...")
    finally:
        server.close()
