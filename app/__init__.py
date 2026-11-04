"""地下網站的 Flask 應用程式。"""

from flask import Flask, render_template


def create_app() -> Flask:
    app = Flask(__name__)

    from app.ctf_center.routes import ctf_center_bp
    from app.website.routes import website_bp

    app.register_blueprint(ctf_center_bp)
    app.register_blueprint(website_bp)

    @app.get("/")
    def portal():
        return render_template("portal.html")

    return app

