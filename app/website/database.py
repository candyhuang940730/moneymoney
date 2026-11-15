import sqlite3
from pathlib import Path
from werkzeug.security import generate_password_hash,check_password_hash
from contextlib import closing
from flask import g
class Database:
    def __init__(self,db_path,schema_path):
        self.db_path = db_path
        self.schema_path = schema_path
    def initialize_db(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self.db_path)) as conn:
            conn.executescript(self.schema_path.read_text(encoding="utf-8"))
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

    #完成後回傳id
    def set_user(self,username,password):
        sql_syntax = "INSERT INTO users (username, password_hash) VALUES (?, ?)"
        db = self.connection()
        password_hash = generate_password_hash(password)
        result = db.execute(sql_syntax,(username, password_hash))
        db.commit()
        return result.lastrowid


    def close_connection(self, error=None):
        conn = g.pop("hydra_conn", None)
        if conn is not None:
            conn.close()