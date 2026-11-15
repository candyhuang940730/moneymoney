"""地下網站的 Flask 應用程式。"""

from flask import Flask, render_template
import os
from pathlib import Path
from app.website.database import Database
from app.website.routes import create_website_blueprint

def create_app() -> Flask:
    app = Flask(__name__)
    db = Database(
    db_path=Path(app.instance_path) / "hydra_db.sqlite3",
        schema_path=Path(app.root_path) / "website" / "schema.sql",
    )
    db.initialize_db()
    app.teardown_appcontext(db.close_connection)
    app.register_blueprint(create_website_blueprint(db))
    app.config["SECRET_KEY"] = os.environ["HYDRA_SECRET_KEY"]
    from app.ctf_center.routes import ctf_center_bp

    app.register_blueprint(ctf_center_bp)


    @app.get("/")
    def portal():
        return render_template("portal.html")


    return app

