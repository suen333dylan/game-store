#!/usr/bin/env python3
"""
猜數字對戰遊戲客戶端 (GUI)
"""
import socket
import json
import sys
import tkinter as tk
from tkinter import messagebox, ttk
import threading

class NumberGuessClient:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.socket = None
        self.player_id = None
        self.my_number = None
        self.guesses = 0
        
        # GUI 元件
        self.root = tk.Tk()
        self.root.title("猜數字對戰")
        self.root.geometry("500x600")
        self.root.resizable(False, False)
        
        self.setup_gui()
        
    def setup_gui(self):
        """設置 GUI 介面"""
        # 標題
        title_label = tk.Label(self.root, text="🎮 猜數字對戰 🎮", 
                               font=("Arial", 24, "bold"), fg="#2c3e50")
        title_label.pack(pady=20)
        
        # 玩家資訊
        self.info_label = tk.Label(self.root, text="連線中...", 
                                   font=("Arial", 12), fg="#7f8c8d")
        self.info_label.pack(pady=10)
        
        # 設定數字區域
        self.setup_frame = tk.Frame(self.root)
        self.setup_frame.pack(pady=20)
        
        tk.Label(self.setup_frame, text="設定你的數字 (1-100):", 
                font=("Arial", 14)).pack()
        
        self.number_entry = tk.Entry(self.setup_frame, font=("Arial", 16), 
                                     width=10, justify="center")
        self.number_entry.pack(pady=10)
        
        self.set_button = tk.Button(self.setup_frame, text="確認設定", 
                                    font=("Arial", 12), bg="#3498db", fg="white",
                                    command=self.set_number, padx=20, pady=5)
        self.set_button.pack()
        
        # 猜測區域
        self.guess_frame = tk.Frame(self.root)
        
        tk.Label(self.guess_frame, text="猜對手的數字:", 
                font=("Arial", 14)).pack()
        
        self.guess_entry = tk.Entry(self.guess_frame, font=("Arial", 16), 
                                    width=10, justify="center")
        self.guess_entry.pack(pady=10)
        
        self.guess_button = tk.Button(self.guess_frame, text="猜測", 
                                      font=("Arial", 12), bg="#2ecc71", fg="white",
                                      command=self.make_guess, padx=20, pady=5)
        self.guess_button.pack()
        
        # 狀態顯示
        self.status_label = tk.Label(self.root, text="", 
                                     font=("Arial", 14, "bold"), fg="#e74c3c")
        self.status_label.pack(pady=20)
        
        # 猜測次數
        self.guesses_label = tk.Label(self.root, text="猜測次數: 0", 
                                      font=("Arial", 12), fg="#34495e")
        self.guesses_label.pack(pady=10)
        
        # 歷史記錄
        history_label = tk.Label(self.root, text="猜測歷史:", 
                                font=("Arial", 12))
        history_label.pack(pady=5)
        
        self.history_text = tk.Text(self.root, height=8, width=50, 
                                    font=("Courier", 10))
        self.history_text.pack(pady=5)
        self.history_text.config(state=tk.DISABLED)
        
    def connect(self):
        """連線到遊戲伺服器"""
        try:
            # 嘗試連線 5 次
            for i in range(5):
                try:
                    self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    self.socket.connect((self.host, self.port))
                    break
                except ConnectionRefusedError:
                    print(f"[DEBUG] 連線被拒 (嘗試 {i+1}/5)，等待 1 秒後重試...")
                    import time
                    time.sleep(1)
            else:
                messagebox.showerror("錯誤", "無法連線到遊戲伺服器")
                self.root.destroy()
                return

            # 接收連線確認
            data = self.socket.recv(4096).decode()
            message = json.loads(data)
            if message["type"] == "connected":
                self.player_id = message["player_id"]
                self.info_label.config(text=f"你是玩家 {self.player_id + 1}", fg="#27ae60")
                return True
        except Exception as e:
            messagebox.showerror("連線錯誤", f"無法連線到伺服器: {e}")
            return False
            
    def set_number(self):
        """設定數字"""
        try:
            number = int(self.number_entry.get())
            if 1 <= number <= 100:
                self.my_number = number
                self.socket.send(json.dumps({
                    "type": "number_set",
                    "number": number
                }).encode())
                
                self.setup_frame.pack_forget()
                self.status_label.config(text="等待對手設定數字...", fg="#f39c12")
                
            else:
                messagebox.showwarning("無效輸入", "請輸入 1-100 之間的數字！")
        except ValueError:
            messagebox.showwarning("無效輸入", "請輸入有效的數字！")
            
    def make_guess(self):
        """進行猜測"""
        try:
            guess = int(self.guess_entry.get())
            if 1 <= guess <= 100:
                self.socket.send(json.dumps({
                    "type": "guess",
                    "number": guess
                }).encode())
                self.guess_entry.delete(0, tk.END)
                self.guess_button.config(state=tk.DISABLED)
                self.add_history(f"第 {self.guesses + 1} 次猜測: {guess}")
            else:
                messagebox.showwarning("無效輸入", "請輸入 1-100 之間的數字！")
        except ValueError:
            messagebox.showwarning("無效輸入", "請輸入有效的數字！")
            
    def add_history(self, text):
        """添加歷史記錄"""
        self.history_text.config(state=tk.NORMAL)
        self.history_text.insert(tk.END, text + "\n")
        self.history_text.see(tk.END)
        self.history_text.config(state=tk.DISABLED)
        
    def handle_messages(self):
        """處理來自伺服器的訊息"""
        while True:
            try:
                data = self.socket.recv(4096).decode()
                if not data:
                    break
                    
                message = json.loads(data)
                
                if message["type"] == "set_number":
                    # 已在 GUI 初始化時處理
                    pass
                    
                elif message["type"] == "start_guessing":
                    self.root.after(0, lambda: self.guess_frame.pack(pady=20))
                    self.root.after(0, lambda: self.status_label.config(
                        text="遊戲開始！輪流猜測對手的數字", fg="#2ecc71"))
                    
                elif message["type"] == "your_turn":
                    self.guesses = message["guesses"]
                    self.root.after(0, lambda: self.guesses_label.config(
                        text=f"猜測次數: {self.guesses}"))
                    self.root.after(0, lambda: self.status_label.config(
                        text="輪到你了！請猜測對手的數字", fg="#3498db"))
                    self.root.after(0, lambda: self.guess_button.config(state=tk.NORMAL))
                    
                elif message["type"] == "wait":
                    self.root.after(0, lambda: self.status_label.config(
                        text=message["message"], fg="#95a5a6"))
                    
                elif message["type"] == "hint":
                    hint = message["hint"]
                    msg = message["message"]
                    self.root.after(0, lambda: self.add_history(f"  → {msg}"))
                    
                elif message["type"] == "game_over":
                    winner = message["winner"]
                    numbers = message["target_numbers"]
                    guesses = message["guesses"]
                    
                    if winner == self.player_id:
                        result = "🎉 你贏了！🎉"
                        color = "#27ae60"
                    else:
                        result = "😢 你輸了！"
                        color = "#e74c3c"
                    
                    details = f"\n玩家1的數字: {numbers[0]}, 猜了 {guesses[0]} 次\n"
                    details += f"玩家2的數字: {numbers[1]}, 猜了 {guesses[1]} 次"
                    
                    self.root.after(0, lambda: self.status_label.config(
                        text=result, fg=color))
                    self.root.after(0, lambda: messagebox.showinfo(
                        "遊戲結束", result + details))
                    self.root.after(0, lambda: self.guess_button.config(state=tk.DISABLED))
                    break
                    
            except Exception as e:
                print(f"[錯誤] {e}")
                break
                
    def run(self):
        """執行客戶端"""
        if self.connect():
            # 在背景執行緒處理伺服器訊息
            thread = threading.Thread(target=self.handle_messages, daemon=True)
            thread.start()
            
            # 啟動 GUI
            self.root.mainloop()
        
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
        port = 5002
    
    print(f"[DEBUG] 啟動GUI客戶端，連線到 {host}:{port}")
    client = NumberGuessClient(host, port)
    try:
        client.run()
    except KeyboardInterrupt:
        print("\n[猜數字對戰客戶端] 正在離開...")
    except Exception as e:
        print(f"[ERROR] 客戶端錯誤: {e}")
        import traceback
        traceback.print_exc()
    finally:
        client.close()
        print("[DEBUG] 客戶端已關閉")
