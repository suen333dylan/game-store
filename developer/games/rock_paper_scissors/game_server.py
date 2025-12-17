#!/usr/bin/env python3
"""
石頭剪刀布多人遊戲伺服器 (支援3-10人)
"""
import socket
import json
import sys
import time

class RockPaperScissorsServer:
    def __init__(self, port, max_players=10, min_players=3):
        self.port = port
        self.max_players = max_players
        self.min_players = min_players
        self.clients = []
        self.player_names = []
        self.server_socket = None
        self.choices = {}  # {player_id: choice}
        self.scores = {}   # {player_id: score}
        
    def start(self):
        """啟動遊戲伺服器"""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind(('0.0.0.0', self.port))
        self.server_socket.listen(self.max_players)
        print(f"[石頭剪刀布伺服器] 在埠口 {self.port} 上啟動")
        print(f"[石頭剪刀布伺服器] 等待 {self.min_players}-{self.max_players} 位玩家...")
        
        # 設定超時，等待玩家連線
        self.server_socket.settimeout(30)
        
        try:
            # 至少需要 min_players 位玩家
            while len(self.clients) < self.max_players:
                try:
                    client_socket, addr = self.server_socket.accept()
                    
                    # 接收玩家名稱
                    data = client_socket.recv(4096).decode()
                    message = json.loads(data)
                    
                    if message["type"] == "join":
                        player_name = message.get("name", f"Player{len(self.clients)+1}")
                        player_id = len(self.clients)
                        
                        self.clients.append(client_socket)
                        self.player_names.append(player_name)
                        self.scores[player_id] = 0
                        
                        print(f"[石頭剪刀布伺服器] {player_name} (玩家 {player_id+1}) 已連線")
                        
                        client_socket.send(json.dumps({
                            "type": "connected",
                            "player_id": player_id,
                            "name": player_name
                        }).encode())
                        
                        # 廣播當前玩家列表
                        self.broadcast({
                            "type": "player_update",
                            "player_count": len(self.clients),
                            "players": self.player_names,
                            "min_players": self.min_players
                        })
                        
                        # 如果達到最少人數，可以開始遊戲
                        if len(self.clients) >= self.min_players:
                            print(f"[石頭剪刀布伺服器] 已達到最少人數 ({self.min_players})，5秒後開始遊戲...")
                            time.sleep(5)
                            break
                            
                except socket.timeout:
                    if len(self.clients) >= self.min_players:
                        print(f"[石頭剪刀布伺服器] 等待超時，以 {len(self.clients)} 位玩家開始遊戲")
                        break
                    else:
                        print(f"[石頭剪刀布伺服器] 等待超時但玩家不足 ({len(self.clients)}/{self.min_players})")
                        self.close()
                        return
        finally:
            self.server_socket.settimeout(None)
        
        if len(self.clients) >= self.min_players:
            print(f"[石頭剪刀布伺服器] 遊戲開始！共 {len(self.clients)} 位玩家")
            self.run_game()
        else:
            print("[石頭剪刀布伺服器] 玩家人數不足，無法開始遊戲")
            self.close()
        
    def determine_winners(self, choices):
        """判定每回合的贏家"""
        # 統計每種選擇的數量
        rock_count = sum(1 for c in choices.values() if c == "rock")
        paper_count = sum(1 for c in choices.values() if c == "paper")
        scissors_count = sum(1 for c in choices.values() if c == "scissors")
        
        # 如果三種都有或只有一種，則平局
        choices_types = (rock_count > 0) + (paper_count > 0) + (scissors_count > 0)
        if choices_types != 2:
            return []  # 平局
        
        # 判定贏家
        winners = []
        if rock_count > 0 and scissors_count > 0 and paper_count == 0:
            # 石頭贏剪刀
            winners = [pid for pid, choice in choices.items() if choice == "rock"]
        elif paper_count > 0 and rock_count > 0 and scissors_count == 0:
            # 布贏石頭
            winners = [pid for pid, choice in choices.items() if choice == "paper"]
        elif scissors_count > 0 and paper_count > 0 and rock_count == 0:
            # 剪刀贏布
            winners = [pid for pid, choice in choices.items() if choice == "scissors"]
        
        return winners
        
    def run_game(self):
        """執行遊戲邏輯"""
        total_rounds = 5
        
        for round_num in range(1, total_rounds + 1):
            print(f"\n[石頭剪刀布伺服器] 第 {round_num}/{total_rounds} 回合開始")
            
            # 通知所有玩家開始新回合
            self.broadcast({
                "type": "new_round",
                "round": round_num,
                "total_rounds": total_rounds,
                "scores": [{"name": self.player_names[i], "score": self.scores[i]} 
                          for i in range(len(self.clients))]
            })
            
            # 收集所有玩家的選擇
            self.choices = {}
            for player_id in range(len(self.clients)):
                try:
                    data = self.clients[player_id].recv(4096).decode()
                    message = json.loads(data)
                    
                    if message["type"] == "choice":
                        self.choices[player_id] = message["choice"]
                        print(f"[石頭剪刀布伺服器] {self.player_names[player_id]} 選擇了 {message['choice']}")
                except Exception as e:
                    print(f"[錯誤] 玩家 {player_id} 斷線: {e}")
                    self.choices[player_id] = "rock"  # 預設選擇
            
            # 判定贏家
            winners = self.determine_winners(self.choices)
            
            # 更新分數
            for winner_id in winners:
                self.scores[winner_id] += 1
            
            # 準備回合結果
            round_result = {
                "type": "round_result",
                "round": round_num,
                "choices": {self.player_names[pid]: choice 
                           for pid, choice in self.choices.items()},
                "winners": [self.player_names[wid] for wid in winners],
                "scores": [{"name": self.player_names[i], "score": self.scores[i]} 
                          for i in range(len(self.clients))]
            }
            
            # 廣播回合結果
            self.broadcast(round_result)
            
            # 等待下一回合
            if round_num < total_rounds:
                time.sleep(3)
        
        # 遊戲結束，判定最終贏家
        max_score = max(self.scores.values())
        final_winners = [i for i, score in self.scores.items() if score == max_score]
        
        self.broadcast({
            "type": "game_over",
            "winners": [self.player_names[wid] for wid in final_winners],
            "final_scores": [{"name": self.player_names[i], "score": self.scores[i]} 
                           for i in range(len(self.clients))]
        })
        
        print(f"\n[石頭剪刀布伺服器] 遊戲結束！")
        print(f"最終贏家: {', '.join([self.player_names[wid] for wid in final_winners])}")
        
        time.sleep(2)
        self.close()
        
    def broadcast(self, message):
        """廣播訊息給所有玩家"""
        data = json.dumps(message).encode()
        for client in self.clients:
            try:
                client.send(data)
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
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5003
    min_players = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    max_players = int(sys.argv[3]) if len(sys.argv) > 3 else 10
    
    server = RockPaperScissorsServer(port, max_players, min_players)
    try:
        server.start()
    except KeyboardInterrupt:
        print("\n[石頭剪刀布伺服器] 正在關閉...")
    finally:
        server.close()
