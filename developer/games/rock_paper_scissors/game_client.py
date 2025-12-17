#!/usr/bin/env python3
"""
石頭剪刀布多人遊戲客戶端 (CLI)
"""
import socket
import json
import sys

class RockPaperScissorsClient:
    def __init__(self, host, port, player_name):
        self.host = host
        self.port = port
        self.player_name = player_name
        self.socket = None
        self.player_id = None
        
    def connect(self):
        """連線到遊戲伺服器"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            
            # 發送加入請求
            self.socket.send(json.dumps({
                "type": "join",
                "name": self.player_name
            }).encode())
            
            # 接收連線確認
            data = self.socket.recv(4096).decode()
            message = json.loads(data)
            if message["type"] == "connected":
                self.player_id = message["player_id"]
                self.player_name = message["name"]
                print(f"\n{'='*50}")
                print(f"🎮 石頭剪刀布大亂鬥 🎮")
                print(f"{'='*50}")
                print(f"歡迎！{self.player_name} (玩家 {self.player_id + 1})")
                print(f"{'='*50}\n")
                return True
        except Exception as e:
            print(f"❌ 連線錯誤: {e}")
            return False
            
    def display_choices_table(self, choices):
        """顯示所有玩家的選擇"""
        print("\n本回合選擇：")
        print("-" * 40)
        emoji_map = {
            "rock": "✊ 石頭",
            "paper": "✋ 布",
            "scissors": "✌️  剪刀"
        }
        for name, choice in choices.items():
            choice_display = emoji_map.get(choice, choice)
            print(f"  {name:15s} : {choice_display}")
        print("-" * 40)
        
    def display_scores(self, scores):
        """顯示分數排行"""
        print("\n目前分數：")
        print("-" * 40)
        # 按分數排序
        sorted_scores = sorted(scores, key=lambda x: x["score"], reverse=True)
        for i, player in enumerate(sorted_scores, 1):
            stars = "⭐" * player["score"]
            print(f"  {i}. {player['name']:15s} : {player['score']} 分 {stars}")
        print("-" * 40)
        
    def play(self):
        """遊戲主邏輯"""
        game_over = False
        
        while not game_over:
            try:
                data = self.socket.recv(4096).decode()
                if not data:
                    break
                    
                message = json.loads(data)
                
                if message["type"] == "player_update":
                    player_count = message["player_count"]
                    min_players = message["min_players"]
                    print(f"\n等待玩家中... ({player_count}/{min_players}+)")
                    print(f"目前玩家: {', '.join(message['players'])}")
                    
                elif message["type"] == "new_round":
                    round_num = message["round"]
                    total_rounds = message["total_rounds"]
                    
                    print(f"\n{'='*50}")
                    print(f"第 {round_num}/{total_rounds} 回合")
                    print(f"{'='*50}")
                    
                    if round_num > 1:
                        self.display_scores(message["scores"])
                    
                    # 讓玩家選擇
                    print("\n請選擇你的出拳：")
                    print("  1. ✊ 石頭 (Rock)")
                    print("  2. ✋ 布 (Paper)")
                    print("  3. ✌️  剪刀 (Scissors)")
                    
                    choice_map = {"1": "rock", "2": "paper", "3": "scissors"}
                    while True:
                        choice_input = input("請輸入 (1/2/3): ").strip()
                        if choice_input in choice_map:
                            choice = choice_map[choice_input]
                            break
                        print("❌ 無效的選擇，請重新輸入！")
                    
                    # 發送選擇
                    self.socket.send(json.dumps({
                        "type": "choice",
                        "choice": choice
                    }).encode())
                    
                    print(f"\n你選擇了: {choice}")
                    print("等待其他玩家...")
                    
                elif message["type"] == "round_result":
                    round_num = message["round"]
                    choices = message["choices"]
                    winners = message["winners"]
                    
                    print(f"\n{'='*50}")
                    print(f"第 {round_num} 回合結果")
                    print(f"{'='*50}")
                    
                    self.display_choices_table(choices)
                    
                    if winners:
                        print(f"\n🎉 本回合贏家: {', '.join(winners)}")
                        if self.player_name in winners:
                            print("恭喜你贏得本回合！ +1 分")
                    else:
                        print("\n🤝 本回合平局！")
                    
                    self.display_scores(message["scores"])
                    
                elif message["type"] == "game_over":
                    winners = message["winners"]
                    final_scores = message["final_scores"]
                    
                    print(f"\n{'='*50}")
                    print(f"🏆 遊戲結束！ 🏆")
                    print(f"{'='*50}")
                    
                    self.display_scores(final_scores)
                    
                    print(f"\n🏆 最終贏家: {', '.join(winners)} 🏆")
                    
                    if self.player_name in winners:
                        print("\n🎊🎊🎊 恭喜你獲勝！🎊🎊🎊")
                    else:
                        print("\n繼續加油！下次一定贏！")
                    
                    print(f"\n{'='*50}\n")
                    game_over = True
                    
            except Exception as e:
                print(f"❌ 錯誤: {e}")
                break
        
    def close(self):
        """關閉連線"""
        if self.socket:
            self.socket.close()

if __name__ == "__main__":
    if len(sys.argv) > 3:
        host = sys.argv[1]
        port = int(sys.argv[2])
        player_name = sys.argv[3]
    elif len(sys.argv) > 2:
        host = sys.argv[1]
        port = int(sys.argv[2])
        player_name = input("請輸入你的名字: ").strip() or f"Player{port%100}"
    else:
        host = "localhost"
        port = 5003
        player_name = input("請輸入你的名字: ").strip() or f"Player{port%100}"
    
    client = RockPaperScissorsClient(host, port, player_name)
    try:
        if client.connect():
            client.play()
    except KeyboardInterrupt:
        print("\n[石頭剪刀布客戶端] 正在離開...")
    finally:
        client.close()
