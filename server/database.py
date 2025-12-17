#!/usr/bin/env python3
"""
資料庫管理模組
使用 SQLite 儲存所有持久化數據
"""
import sqlite3
import json
import hashlib
import os
from datetime import datetime

class Database:
    def __init__(self, db_path="database/gamestore.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.init_database()
    
    def get_connection(self):
        """獲取資料庫連線"""
        return sqlite3.connect(self.db_path)
    
    def init_database(self):
        """初始化資料庫表格"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # 開發者帳號表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS developers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 玩家帳號表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS players (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 遊戲表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS games (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                game_name TEXT UNIQUE NOT NULL,
                developer_id INTEGER NOT NULL,
                current_version TEXT NOT NULL,
                description TEXT,
                game_type TEXT,
                min_players INTEGER,
                max_players INTEGER,
                server_port INTEGER,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (developer_id) REFERENCES developers(id)
            )
        ''')
        
        # 遊戲版本表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS game_versions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                game_id INTEGER NOT NULL,
                version TEXT NOT NULL,
                file_path TEXT NOT NULL,
                upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (game_id) REFERENCES games(id),
                UNIQUE(game_id, version)
            )
        ''')
        
        # 遊戲評分表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS game_ratings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                game_id INTEGER NOT NULL,
                player_id INTEGER NOT NULL,
                rating INTEGER CHECK(rating >= 1 AND rating <= 5),
                comment TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (game_id) REFERENCES games(id),
                FOREIGN KEY (player_id) REFERENCES players(id),
                UNIQUE(game_id, player_id)
            )
        ''')
        
        # 玩家下載記錄表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS download_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_id INTEGER NOT NULL,
                game_id INTEGER NOT NULL,
                version TEXT NOT NULL,
                download_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (player_id) REFERENCES players(id),
                FOREIGN KEY (game_id) REFERENCES games(id)
            )
        ''')
        
        conn.commit()
        conn.close()
        print("[資料庫] 初始化完成")
    
    def hash_password(self, password):
        """密碼雜湊"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    # ===== 開發者相關操作 =====
    
    def register_developer(self, username, password):
        """註冊開發者帳號"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            password_hash = self.hash_password(password)
            cursor.execute(
                "INSERT INTO developers (username, password_hash) VALUES (?, ?)",
                (username, password_hash)
            )
            conn.commit()
            return True, "註冊成功"
        except sqlite3.IntegrityError:
            return False, "帳號已存在"
        finally:
            conn.close()
    
    def login_developer(self, username, password):
        """開發者登入"""
        conn = self.get_connection()
        cursor = conn.cursor()
        password_hash = self.hash_password(password)
        cursor.execute(
            "SELECT id, username FROM developers WHERE username = ? AND password_hash = ?",
            (username, password_hash)
        )
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return True, {"id": result[0], "username": result[1]}
        return False, "帳號或密碼錯誤"
    
    # ===== 玩家相關操作 =====
    
    def register_player(self, username, password):
        """註冊玩家帳號"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            password_hash = self.hash_password(password)
            cursor.execute(
                "INSERT INTO players (username, password_hash) VALUES (?, ?)",
                (username, password_hash)
            )
            conn.commit()
            return True, "註冊成功"
        except sqlite3.IntegrityError:
            return False, "帳號已存在"
        finally:
            conn.close()
    
    def login_player(self, username, password):
        """玩家登入"""
        conn = self.get_connection()
        cursor = conn.cursor()
        password_hash = self.hash_password(password)
        cursor.execute(
            "SELECT id, username FROM players WHERE username = ? AND password_hash = ?",
            (username, password_hash)
        )
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return True, {"id": result[0], "username": result[1]}
        return False, "帳號或密碼錯誤"
    
    # ===== 遊戲相關操作 =====
    
    def create_game(self, game_name, developer_id, version, description, game_type, 
                    min_players, max_players, server_port, file_path):
        """建立新遊戲"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            # 檢查遊戲名稱是否已存在（包括已下架的）
            cursor.execute("SELECT id, is_active FROM games WHERE game_name = ?", (game_name,))
            existing = cursor.fetchone()
            if existing:
                game_id, is_active = existing
                if is_active:
                    return False, "遊戲名稱已存在"
                else:
                    # 已下架的遊戲，重新啟用
                    cursor.execute('''
                        UPDATE games 
                        SET current_version = ?, description = ?, game_type = ?,
                            min_players = ?, max_players = ?, server_port = ?, is_active = 1
                        WHERE id = ?
                    ''', (version, description, game_type, min_players, max_players, server_port, game_id))
                    
                    # 新增版本記錄
                    cursor.execute('''
                        INSERT INTO game_versions (game_id, version, file_path)
                        VALUES (?, ?, ?)
                    ''', (game_id, version, file_path))
                    
                    conn.commit()
                    return True, game_id
            
            # 插入遊戲資料
            cursor.execute('''
                INSERT INTO games (game_name, developer_id, current_version, description, 
                                  game_type, min_players, max_players, server_port)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (game_name, developer_id, version, description, game_type, 
                  min_players, max_players, server_port))
            
            game_id = cursor.lastrowid
            
            # 插入版本記錄
            cursor.execute('''
                INSERT INTO game_versions (game_id, version, file_path)
                VALUES (?, ?, ?)
            ''', (game_id, version, file_path))
            
            conn.commit()
            return True, game_id
        except Exception as e:
            conn.rollback()
            return False, str(e)
        finally:
            conn.close()
    
    def update_game_version(self, game_id, developer_id, new_version, file_path):
        """更新遊戲版本"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            # 驗證開發者權限
            cursor.execute(
                "SELECT developer_id FROM games WHERE id = ?", (game_id,))
            result = cursor.fetchone()
            if not result or result[0] != developer_id:
                return False, "無權限更新此遊戲"
            
            # 更新遊戲當前版本
            cursor.execute('''
                UPDATE games SET current_version = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (new_version, game_id))
            
            # 新增版本記錄
            cursor.execute('''
                INSERT INTO game_versions (game_id, version, file_path)
                VALUES (?, ?, ?)
            ''', (game_id, new_version, file_path))

            # 已下架的遊戲重新上架
            cursor.execute('''
                UPDATE games SET is_active = 1 WHERE id = ?
            ''', (game_id,))
            
            conn.commit()
            return True, "更新成功"
        except sqlite3.IntegrityError:
            return False, "版本號已存在"
        except Exception as e:
            conn.rollback()
            return False, str(e)
        finally:
            conn.close()
    
    def deactivate_game(self, game_id, developer_id):
        """下架遊戲"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            # 驗證開發者權限
            cursor.execute(
                "SELECT developer_id FROM games WHERE id = ?", (game_id,))
            result = cursor.fetchone()
            if not result or result[0] != developer_id:
                return False, "無權限下架此遊戲"
            
            cursor.execute(
                "UPDATE games SET is_active = 0 WHERE id = ?", (game_id,))
            conn.commit()
            return True, "下架成功"
        except Exception as e:
            conn.rollback()
            return False, str(e)
        finally:
            conn.close()
    
    def get_active_games(self):
        """獲取所有上架中的遊戲"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT g.id, g.game_name, d.username, g.current_version, g.description,
                   g.game_type, g.min_players, g.max_players, g.server_port,
                   AVG(r.rating) as avg_rating, COUNT(r.id) as rating_count
            FROM games g
            JOIN developers d ON g.developer_id = d.id
            LEFT JOIN game_ratings r ON g.id = r.game_id
            WHERE g.is_active = 1
            GROUP BY g.id
        ''')
        
        games = []
        for row in cursor.fetchall():
            games.append({
                "id": row[0],
                "name": row[1],
                "author": row[2],
                "version": row[3],
                "description": row[4],
                "type": row[5],
                "min_players": row[6],
                "max_players": row[7],
                "server_port": row[8],
                "avg_rating": round(row[9], 1) if row[9] else 0,
                "rating_count": row[10]
            })
        
        conn.close()
        return games
    
    def get_game_by_id(self, game_id):
        """根據ID獲取遊戲資訊"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT g.id, g.game_name, d.username, g.current_version, g.description,
                   g.game_type, g.min_players, g.max_players, g.server_port, g.is_active
            FROM games g
            JOIN developers d ON g.developer_id = d.id
            WHERE g.id = ?
        ''', (game_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                "id": row[0],
                "name": row[1],
                "author": row[2],
                "version": row[3],
                "description": row[4],
                "type": row[5],
                "min_players": row[6],
                "max_players": row[7],
                "server_port": row[8],
                "is_active": row[9]
            }
        return None
    
    def get_developer_games(self, developer_id):
        """獲取開發者的所有遊戲"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, game_name, current_version, description, game_type,
                   min_players, max_players, is_active, created_at
            FROM games
            WHERE developer_id = ?
            ORDER BY created_at DESC
        ''', (developer_id,))
        
        games = []
        for row in cursor.fetchall():
            games.append({
                "id": row[0],
                "name": row[1],
                "version": row[2],
                "description": row[3],
                "type": row[4],
                "min_players": row[5],
                "max_players": row[6],
                "is_active": bool(row[7]),
                "created_at": row[8]
            })
        
        conn.close()
        return games
    
    # ===== 評分相關操作 =====
    
    def add_rating(self, game_id, player_id, rating, comment=""):
        """新增遊戲評分"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO game_ratings (game_id, player_id, rating, comment)
                VALUES (?, ?, ?, ?)
            ''', (game_id, player_id, rating, comment))
            conn.commit()
            return True, "評分成功"
        except Exception as e:
            conn.rollback()
            return False, str(e)
        finally:
            conn.close()
    
    def get_game_ratings(self, game_id, limit=10):
        """獲取遊戲評分與評論"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT p.username, r.rating, r.comment, r.created_at
            FROM game_ratings r
            JOIN players p ON r.player_id = p.id
            WHERE r.game_id = ?
            ORDER BY r.created_at DESC
            LIMIT ?
        ''', (game_id, limit))
        
        ratings = []
        for row in cursor.fetchall():
            ratings.append({
                "player": row[0],
                "rating": row[1],
                "comment": row[2],
                "date": row[3]
            })
        
        conn.close()
        return ratings
    
    # ===== 下載記錄相關操作 =====
    
    def record_download(self, player_id, game_id, version):
        """記錄玩家下載遊戲"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO download_records (player_id, game_id, version)
                VALUES (?, ?, ?)
            ''', (player_id, game_id, version))
            conn.commit()
            return True
        except Exception as e:
            return False
        finally:
            conn.close()
    
    def get_player_downloads(self, player_id):
        """獲取玩家的下載記錄"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT g.id, g.game_name, g.current_version, dr.version, dr.download_time
            FROM download_records dr
            JOIN games g ON dr.game_id = g.id
            WHERE dr.player_id = ?
            ORDER BY dr.download_time DESC
        ''', (player_id,))
        
        downloads = []
        for row in cursor.fetchall():
            downloads.append({
                "game_id": row[0],
                "game_name": row[1],
                "current_version": row[2],
                "downloaded_version": row[3],
                "download_time": row[4]
            })
        
        conn.close()
        return downloads

if __name__ == "__main__":
    # 測試資料庫
    db = Database()
    print("資料庫測試完成")
