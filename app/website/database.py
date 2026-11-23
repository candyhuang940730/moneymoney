import sqlite3
from pathlib import Path
from werkzeug.security import generate_password_hash,check_password_hash
from contextlib import closing
from flask import g

DEFAULT_ADMIN_USERNAME = "Admin_is_god"
DEFAULT_ADMIN_PASSWORD = "god_789!@#"


class Database:
    def __init__(self,db_path,schema_path):
        self.db_path = db_path
        self.schema_path = schema_path
    def initialize_db(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self.db_path)) as conn:
            conn.executescript(self.schema_path.read_text(encoding="utf-8"))
            admin_exists = conn.execute(
                "SELECT 1 FROM users WHERE UserName = ?", (DEFAULT_ADMIN_USERNAME,)
            ).fetchone()
            if admin_exists is None:
                conn.execute(
                    """INSERT INTO users (UserName, password_hash, is_admin, is_active)
                    VALUES (?, ?, 1, 1)
                    ON CONFLICT(UserName) DO NOTHING""",
                    (
                        DEFAULT_ADMIN_USERNAME,
                        generate_password_hash(DEFAULT_ADMIN_PASSWORD),
                    ),
                )
            conn.commit()
    def connection(self):
        if "hydra_conn" not in g:
            g.hydra_conn = sqlite3.connect(self.db_path)
            g.hydra_conn.row_factory = sqlite3.Row
        return g.hydra_conn

    def verify_user(self, username, password):
        user = self.search_by_username(username)
        if user is None or not user["is_active"]:
            return None
        if not check_password_hash(user["password_hash"], password):
            return None
        return user

    def search_by_id(self,id):
        sql = """SELECT id, UserName, is_active, is_admin, user_role
        FROM users 
        WHERE id = ?
        """
        db = self.connection()
        data = db.execute(sql,(id,)).fetchone()
        return data

    def search_by_username(self,username):
        sql = "SELECT * FROM users WHERE UserName = ?"
        db = self.connection()
        data = db.execute(sql,(username,)).fetchone()
        return data

    # 建立使用者後回傳 id；公開註冊的角色由 add_user 固定指定。
    def set_user(self,username,password,user_role):
        sql_syntax = "INSERT INTO users (UserName, password_hash, user_role, is_admin, is_active) VALUES (?, ?, ?, 0, 1)"
        db = self.connection()
        password_hash = generate_password_hash(password)
        result = db.execute(sql_syntax, (username, password_hash, user_role))
        db.commit()
        return result.lastrowid

    def add_user(self,username,password,checkpassword):
        """公開註冊買家；成功回傳 None，驗證失敗回傳訊息。"""
        username = username.strip()
        if not username:
            return "帳號不應為空"
        if len(username) < 3 or len(username) > 32 or any(char.isspace() for char in username):
            return "帳號需為 3 至 32 個字元，且不能包含空白"
        if not password.strip():
            return "密碼不應為空"
        if len(password) < 8 or len(password) > 128:
            return "密碼需為 8 至 128 個字元"
        if password != checkpassword:
            return "確認密碼錯誤"
        try:
            self.set_user(username, password, "buyer")
        except sqlite3.IntegrityError as exc:
            if "UNIQUE constraint failed" in str(exc):
                return "帳號已被使用"
            raise
        return None

    def close_connection(self, error=None):
        conn = g.pop("hydra_conn", None)
        if conn is not None:
            conn.close()
