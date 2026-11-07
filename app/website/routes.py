import json
from pathlib import Path
from flask import Blueprint, jsonify, render_template

website_bp = Blueprint("website", __name__, url_prefix="/site")


def load_products() -> list[dict]:
    """從 products.json 檔案動態讀取商品資料清單。"""
    candidate_paths = [
        Path(__file__).resolve().parent.parent.parent / "products.json",
        Path(__file__).resolve().parent.parent / "data" / "products.json",
    ]
    for path in candidate_paths:
        if path.is_file():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
    return []


@website_bp.get("/")
def index():
    return render_template("website/login.html")


@website_bp.route("/products", methods=["GET", "POST"])
def products():
    items = load_products()
    return render_template("website/products.html", products=items)


@website_bp.get("/api/products")
def api_products():
    return jsonify(load_products())
