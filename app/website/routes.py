from flask import Blueprint, redirect, render_template, request, session, url_for
from app.website.database import Database


def create_website_blueprint(db: Database):
    website_bp = Blueprint("website", __name__, url_prefix="/site")

    def load_site_user():
        user_id = session.get("site_user_id")
        if user_id is None:
            return None

        user = db.search_by_id(user_id)
        if user is None or not user["is_active"]:
            session.pop("site_user_id", None)
            return None
        return user

    @website_bp.get("/")
    def index():
        return render_template("website/login.html", current_user=load_site_user())

    @website_bp.post("/login")
    def login():
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        result = db.verify_user(username, password)
        if result is None:
            return render_template(
                "website/login.html",
                login_error="帳號或密碼錯誤",
            ), 401

        session.clear()
        session["site_user_id"] = result["id"]
        return redirect(url_for("website.index"))

    @website_bp.post("/logout")
    def logout():
        session.pop("site_user_id", None)
        return redirect(url_for("website.index"))

    return website_bp
