import sqlite3
from pathlib import Path
from werkzeug.security import generate_password_hash,check_password_hash
class database:
    def __init__(self):
        self.db_path = Path(__file__).parent/"data/hydra_db.sqlite3"
        self.init_db()
        self.set_data_row()
        pass
    def init_db(self):
        db_path = self.db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(db_path)
        schema_path = Path(__file__).parent / "schema.sql"
        self.db.executescript(schema_path.read_text(encoding="utf-8"))

    def verify_user(self, username, password):
        user = self.search_by_username(username)
        if user is None or not user["is_active"]:
            return None
        if not check_password_hash(user["password_hash"], password):
            return None
        return user

    def search_by_id(self,id):
        sql = "SELECT * FROM users WHERE id = ?"
        data = self.db.execute(sql,(id,)).fetchone()
        return data

    def search_by_username(self,username):
        sql = "SELECT * FROM users WHERE UserName = ?"
        data = self.db.execute(sql,(username,)).fetchone()
        return data

    #完成後回傳id
    def set_user(self,username,password):
        sql_syntax = "INSERT INTO users (username, password_hash) VALUES (?, ?)"
        password_hash = generate_password_hash(password)
        result = self.db.execute(sql_syntax,(username, password_hash))
        self.db.commit()
        return result.lastrowid

    def set_data_row(self):
        self.db.row_factory = sqlite3.Row

    def close_db(self):
        self.db.close()