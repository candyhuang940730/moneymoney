import json
import math
from pathlib import Path
from flask import Blueprint, jsonify, redirect, render_template, request, session, url_for
from app.website.database import Database


def load_products() -> list[dict]:
    """優先從 app/data/products.json 動態讀取商品資料清單。"""
    candidate_paths = [
        Path(__file__).resolve().parent.parent / "data" / "products.json",
        Path(__file__).resolve().parent.parent / "data" / "products-example.json",
        Path(__file__).resolve().parent.parent.parent / "products.json",
        Path(__file__).resolve().parent.parent.parent / "products-example.json",
    ]
    for path in candidate_paths:
        if path.is_file():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if data:
                        return data
            except Exception:
                pass
    return []


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

    # 商品清單頁面（BTC 計價，正常商品頁面初始 0 BTC）
    @website_bp.route("/products", methods=["GET", "POST"])
    def products():
        items = load_products()
        balance = 0
        return render_template(
            "website/products.html",
            products=items,
            balance=balance,
        )

    # 商品 AJAX 分頁 API
    @website_bp.get("/api/products")
    def api_products():
        items = load_products()
        page = request.args.get("page", type=int)
        per_page = request.args.get("per_page", default=9, type=int)
        if page is not None and page > 0:
            total = len(items)
            total_pages = math.ceil(total / per_page) if per_page > 0 else 1
            start = (page - 1) * per_page
            end = start + per_page
            return jsonify({
                "items": items[start:end],
                "page": page,
                "per_page": per_page,
                "total": total,
                "total_pages": total_pages,
            })
        return jsonify(items)

    return website_bp
