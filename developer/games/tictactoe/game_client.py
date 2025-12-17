#!/usr/bin/env python3
"""
井字遊戲客戶端 (CLI)
"""
import socket
import json
import sys

class TicTacToeClient:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.socket = None
        self.player_id = None
        self.symbol = None
        
    def receive_message(self):
        """接收並解析 JSON 訊息"""
        chunks = []
        self.socket.settimeout(30.0)  # 設置 30 秒超時
        while True:
            try:
                chunk = self.socket.recv(4096).decode('utf-8')
                if not chunk:
                    print("[DEBUG] 收到空數據，連線關閉")
                    return None
                print(f"[DEBUG] 收到數據塊 ({len(chunk)} bytes): {chunk[:100]}...")
                chunks.append(chunk)
                full_data = ''.join(chunks)
                # 嘗試解析，如果成功返回第一個完整的 JSON 對象
                try:
                    message = json.loads(full_data)
                    return message
                except json.JSONDecodeError as e:
                    # 如果是 Extra data 錯誤，說明收到多個 JSON，取第一個
                    if "Extra data" in str(e):
                        # 找到第一個完整 JSON 的結束位置
                        try:
                            decoder = json.JSONDecoder()
                            message, idx = decoder.raw_decode(full_data)
                            return message
                        except:
                            continue
                    # 否則繼續接收
                    continue
            except socket.timeout:
                print("❌ 接收超時")
                return None
            except Exception as e:
                print(f"❌ 接收錯誤: {e}")
                return None
    
    def connect(self):
        """連線到遊戲伺服器"""
        print(f"[DEBUG] 正在連線到 {self.host}:{self.port}...")
        
        # 嘗試連線 5 次
        for i in range(5):
            try:
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.socket.connect((self.host, self.port))
                print("[DEBUG] 連線成功，等待伺服器確認...")
                break
            except ConnectionRefusedError:
                print(f"[DEBUG] 連線被拒 (嘗試 {i+1}/5)，等待 1 秒後重試...")
                import time
                time.sleep(1)
            except Exception as e:
                print(f"❌ 連線錯誤: {e}")
                return False
        else:
            print("❌ 無法連線到遊戲伺服器 (重試次數過多)")
            return False
        
        # 接收連線確認
        message = self.receive_message()
        print(f"[DEBUG] 收到連線確認: {message}")
        if message["type"] == "connected":
            self.player_id = message["player_id"]
            self.symbol = message["symbol"]
            print(f"\n========== 井字遊戲 ==========")
            print(f"你是玩家 {self.player_id + 1}，你的符號是 '{self.symbol}'")
            print(f"=============================\n")
            return True
        return False
        
    def display_board(self, board):
        """顯示棋盤"""
        print("\n  當前棋盤：")
        print("     0   1   2")
        print("   +---+---+---+")
        for i, row in enumerate(board):
            print(f" {i} | {row[0]} | {row[1]} | {row[2]} |")
            print("   +---+---+---+")
        print()
        
    def play(self):
        """遊戲主邏輯"""
        game_over = False
        
        while not game_over:
            # 接收遊戲狀態
            message = self.receive_message()
            if not message:
                print("❌ 連線斷開")
                break
            
            if message["type"] == "board_update":
                board = message["board"]
                current_player = message["current_player"]
                
                self.display_board(board)
                
                if current_player == self.player_id:
                    # 輪到我下棋
                    while True:
                        try:
                            print(f"輪到你了！({self.symbol})")
                            row = int(input("請輸入行號 (0-2): "))
                            col = int(input("請輸入列號 (0-2): "))
                            
                            # 發送移動
                            self.socket.sendall(json.dumps({
                                "type": "move",
                                "row": row,
                                "col": col
                            }).encode())
                            
                            # 等待確認或錯誤訊息
                            response = self.receive_message()
                            if not response:
                                print("❌ 連線斷開")
                                game_over = True
                                break
                            
                            if response["type"] == "invalid_move":
                                print(f"❌ {response['message']}")
                                continue
                            elif response["type"] == "board_update" or response["type"] == "game_over":
                                # 移動成功，處理新狀態
                                if response["type"] == "game_over":
                                    self.handle_game_over(response)
                                    game_over = True
                                break
                        except ValueError:
                            print("❌ 請輸入有效的數字！")
                        except Exception as e:
                            print(f"❌ 錯誤: {e}")
                            break
                else:
                    print("等待對手下棋...")
                    
            elif message["type"] == "game_over":
                self.handle_game_over(message)
                game_over = True
                
    def handle_game_over(self, message):
        """處理遊戲結束"""
        self.display_board(message["board"])
        
        if message["reason"] == "draw":
            print("\n========== 平局！ ==========\n")
        else:
            winner_id = message["winner"]
            if winner_id == self.player_id:
                print("\n🎉 ========== 你贏了！ ========== 🎉\n")
            else:
                print("\n😢 ========== 你輸了！ ========== 😢\n")
        
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
        port = 5001
    
    client = TicTacToeClient(host, port)
    try:
        if client.connect():
            client.play()
    except KeyboardInterrupt:
        print("\n[井字遊戲客戶端] 正在離開...")
    except Exception as e:
        print(f"[錯誤] {e}")
    finally:
        client.close()
