#!/usr/bin/env python3
"""
井字遊戲伺服器 (CLI 雙人遊戲)
"""
import socket
import threading
import json
import sys

class TicTacToeServer:
    def __init__(self, port):
        self.port = port
        self.clients = []
        self.board = [[' ' for _ in range(3)] for _ in range(3)]
        self.current_player = 0
        self.symbols = ['X', 'O']
        self.server_socket = None
        
    def start(self):
        """啟動遊戲伺服器"""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind(('0.0.0.0', self.port))
        self.server_socket.listen(5)
        print(f"[井字遊戲伺服器] 在埠口 {self.port} 上啟動")
        
        # 等待兩位玩家連線
        while len(self.clients) < 2:
            try:
                client_socket, addr = self.server_socket.accept()
                print(f"[井字遊戲伺服器] 接受連線: {addr}")
                
                # 發送連線確認
                player_id = len(self.clients)
                symbol = self.symbols[player_id]
                
                client_socket.sendall(json.dumps({
                    "type": "connected",
                    "player_id": player_id,
                    "symbol": symbol
                }).encode())
                
                # 等待客戶端確認 (過濾掉 wait_for_port 的探測連線)
                client_socket.settimeout(3.0)
                try:
                    data = client_socket.recv(1024)
                    if not data:
                        print(f"[井字遊戲伺服器] 連線已關閉 (可能是探測連線)")
                        client_socket.close()
                        continue
                        
                    msg = json.loads(data.decode())
                    if msg.get("type") == "ready":
                        client_socket.settimeout(None) # 移除超時
                        self.clients.append(client_socket)
                        print(f"[井字遊戲伺服器] 玩家 {player_id+1} ({symbol}) 已加入")
                    else:
                        print(f"[井字遊戲伺服器] 收到無效握手訊息")
                        client_socket.close()
                except socket.timeout:
                    print(f"[井字遊戲伺服器] 等待握手超時")
                    client_socket.close()
                except Exception as e:
                    print(f"[井字遊戲伺服器] 握手錯誤: {e}")
                    client_socket.close()
                    
            except Exception as e:
                print(f"[井字遊戲伺服器] Accept 錯誤: {e}")
        
        print("[井字遊戲伺服器] 遊戲開始！")
        self.run_game()
        
    def check_winner(self):
        """檢查是否有贏家"""
        # 檢查行
        for row in self.board:
            if row[0] == row[1] == row[2] != ' ':
                return row[0]
        
        # 檢查列
        for col in range(3):
            if self.board[0][col] == self.board[1][col] == self.board[2][col] != ' ':
                return self.board[0][col]
        
        # 檢查對角線
        if self.board[0][0] == self.board[1][1] == self.board[2][2] != ' ':
            return self.board[0][0]
        if self.board[0][2] == self.board[1][1] == self.board[2][0] != ' ':
            return self.board[0][2]
        
        return None
        
    def is_board_full(self):
        """檢查棋盤是否已滿"""
        for row in self.board:
            if ' ' in row:
                return False
        return True
        
    def run_game(self):
        """執行遊戲邏輯"""
        game_over = False
        
        while not game_over:
            # 廣播當前棋盤狀態
            print(f"[DEBUG] 廣播棋盤狀態，當前玩家: {self.current_player}")
            self.broadcast({
                "type": "board_update",
                "board": self.board,
                "current_player": self.current_player
            })
            
            # 等待當前玩家下棋
            try:
                print(f"[DEBUG] 等待玩家 {self.current_player} 下棋...")
                try:
                    raw = self.clients[self.current_player].recv(4096)
                    if not raw:
                        print(f"[錯誤] 玩家 {self.current_player} 連線中斷 (收到 0 bytes)")
                        game_over = True
                        break
                    data = raw.decode()
                    print(f"[DEBUG] 收到玩家 {self.current_player} 的數據: {data[:100]}...")
                    try:
                        move = json.loads(data)
                    except json.JSONDecodeError:
                        print(f"[錯誤] 無效的 JSON，等待玩家重傳")
                        # 要求玩家重傳（或簡單忽略並繼續迴圈）
                        self.clients[self.current_player].sendall(json.dumps({
                            "type": "error",
                            "message": "invalid_json"
                        }).encode())
                        continue
                except Exception as recv_exc:
                    print(f"[錯誤] recv 發生例外: {recv_exc}")
                    game_over = True
                    break
                
                if move["type"] == "move":
                    row, col = move["row"], move["col"]
                    
                    # 驗證移動是否合法
                    if 0 <= row < 3 and 0 <= col < 3 and self.board[row][col] == ' ':
                        self.board[row][col] = self.symbols[self.current_player]
                        
                        # 檢查遊戲結束條件
                        winner = self.check_winner()
                        if winner:
                            self.broadcast({
                                "type": "game_over",
                                "winner": self.symbols.index(winner),
                                "board": self.board,
                                "reason": "win"
                            })
                            game_over = True
                        elif self.is_board_full():
                            self.broadcast({
                                "type": "game_over",
                                "winner": -1,
                                "board": self.board,
                                "reason": "draw"
                            })
                            game_over = True
                        else:
                            # 切換玩家
                            self.current_player = 1 - self.current_player
                    else:
                        # 非法移動，要求重新下棋
                        self.clients[self.current_player].sendall(json.dumps({
                            "type": "invalid_move",
                            "message": "該位置已被佔用或超出範圍"
                        }).encode())
            except Exception as e:
                print(f"[錯誤] {e}")
                game_over = True
        
        print("[井字遊戲伺服器] 遊戲結束")
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
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5001
    server = TicTacToeServer(port)
    try:
        server.start()
    except KeyboardInterrupt:
        print("\n[井字遊戲伺服器] 正在關閉...")
    finally:
        server.close()
