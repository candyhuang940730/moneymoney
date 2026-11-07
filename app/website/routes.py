import json
from pathlib import Path
from flask import Blueprint, jsonify, render_template

website_bp = Blueprint("website", __name__, url_prefix="/site")


def load_products() -> list[dict]:
    """從 products-example.json 檔案動態讀取商品資料清單。"""
    candidate_files = [
        "products-example.json",
        "products.json",
    ]
    candidate_dirs = [
        Path(__file__).resolve().parent.parent.parent,
        Path(__file__).resolve().parent.parent / "data",
    ]
    for filename in candidate_files:
        for directory in candidate_dirs:
            path = directory / filename
            if path.is_file():
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        if data:
                            return data
                except Exception:
                    pass
    return []


@website_bp.get("/")
def index():
    return render_template("website/login.html")


# 依需求移除由登入頁面直接導向商品頁的路由，保留原始登入頁規範
# （登入與身分驗證留待後續章節實作，不直接放行至商品頁）


@website_bp.route("/products", methods=["GET", "POST"])
def products():
    # 讀取範例檔案商品資料
    items = load_products()

    # --- 身分檢查與切換邏輯（已依需求註解，僅展示一般正常商品頁面）---
    # target_role = request.args.get("role", "").lower()
    # target_user = request.args.get("user", "").lower()
    # if target_role == "admin" or target_user == "admin":
    #     session["user"] = "admin"
    #     session["is_admin"] = True
    #     session["balance"] = 60000
    # elif target_role in ("guest", "user") or target_user in ("guest", "user"):
    #     session["user"] = "guest"
    #     session["is_admin"] = False
    #     session["balance"] = 0
    # ------------------------------------------------------------------

    # 正常商品頁面初始餘額為 0 BTC
    balance = 0

    return render_template(
        "website/products.html",
        products=items,
        balance=balance,
    )


@website_bp.get("/api/products")
def api_products():
    return jsonify(load_products())
