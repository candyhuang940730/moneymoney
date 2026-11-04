"""地下網站的 Flask 應用程式。"""

from flask import Flask


def create_app() -> Flask:
    app = Flask(__name__)

    from app.website.routes import website_bp

    app.register_blueprint(website_bp)
    return app

