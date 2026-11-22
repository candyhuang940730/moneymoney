import json
import math
import os
from pathlib import Path
from functools import wraps
from flask import (
    Blueprint,
    jsonify,
    make_response,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from app.website.database import Database

# FLAG 只存在伺服器端，部署時用環境變數 HYDRA_FLAG_2 覆寫
FLAG_2 = os.environ.get("HYDRA_FLAG_2", "FLAG{Logic_Is_Wealth_In_Darkness}")


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
    
    def login_required(view):
        @wraps(view)
        def wrapper(*args, **kwargs):
            if load_site_user() is None:
                if request.path.startswith("/site/api/"):
                    return jsonify({"success": False, "message": "請先登入"}), 401
                return redirect(url_for("website.index"))
            return view(*args, **kwargs)
        return wrapper

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
    @login_required
    def products():
        items = load_products()
        current_site_user = load_site_user()
        balance = session.get("balance", 0)

        response = make_response(
            render_template(
                "website/products.html",
                products=items,
                balance=balance,
                current_user=current_site_user,
            )
        )

        # 靜默設定 Cookie 權限憑證：預設為受限節點 standard
        # 滲透測試者/玩家需透過 DevTools 或封包攔截發現並竄改此 Cookie (如 hydra_tier=admin 或 root)
        if "hydra_tier" not in request.cookies:
            response.set_cookie("hydra_tier", "standard", samesite="Lax")

        return response

    # 商品 AJAX 分頁 API
    @website_bp.get("/api/products")
    @login_required
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

    # 商品購買 API（第二章：資本累積 - 包含角色權限限制與業務邏輯漏洞）
    @website_bp.post("/api/buy")
    @login_required
    def api_buy():
        data = request.get_json(silent=True) or request.form.to_dict() or {}
        product_id = str(data.get("product_id", "")).strip()

        items = load_products()
        product = next((it for it in items if it["id"] == product_id), None)
        if not product:
            return jsonify({"success": False, "message": "商品不存在或已自黑市下架。"}), 404

        # 隱密身分提權判定：
        # 1. 主向量：Cookie 竄改 (hydra_tier=admin / root / tier-root)
        # 2. 次向量：Mass Assignment (JSON 請求體攜帶 role="admin" 或 is_admin=true)
        # 3. 正常已登入系統管理員帳號
        cookie_tier = request.cookies.get("hydra_tier", "standard").strip().lower()
        body_role = str(data.get("role", "")).strip().lower()
        body_is_admin = bool(data.get("is_admin", False))
        current_site_user = load_site_user()

        is_admin = bool(
            cookie_tier in ("admin", "root", "tier-root", "tier_root")
            or body_role in ("admin", "root")
            or body_is_admin
            or (current_site_user and current_site_user["is_admin"])
        )

        # 解析數量
        try:
            quantity = int(data.get("quantity", 1))
        except (ValueError, TypeError):
            quantity = 1

        # 解析自訂價格
        has_custom_price = False
        if "price" in data and data.get("price") is not None:
            try:
                unit_price = int(data["price"])
                if unit_price != product["price"]:
                    has_custom_price = True
            except (ValueError, TypeError):
                unit_price = product["price"]
        else:
            unit_price = product["price"]

        # --- 角色限制檢驗 (Role Restriction) ---
        # 錯誤訊息維持暗網合約風格，不主動劇透提權路徑
        # 1. 目標資產限制：HU-PRD-027「高階密碼本」僅限特權節點 (TIER-ROOT) 採購
        if product_id == "HU-PRD-027" and not is_admin:
            return jsonify({
                "success": False,
                "message": "結算合約中斷：授權驗證失敗，當前連線憑證未附帶 TIER-ROOT 存取權杖 (ERR_CONTRACT_TIER_RESTRICTED)。",
            }), 403

        # 2. 報價覆寫限制：非特權節點禁止竄改價格 (Parameter Tampering 需在具備特權時方可生效)
        if has_custom_price and not is_admin:
            return jsonify({
                "success": False,
                "message": "結算合約拒絕：單價與鏈上標價不符，非特權節點無權重寫單價 (ERR_PRICE_TAMPERING_REJECTED)。",
            }), 403

        # 3. 負數沖銷限制：非特權節點禁止輸入非正數數量
        if quantity < 1 and not is_admin:
            return jsonify({
                "success": False,
                "message": "結算合約中斷：數量參數校驗未通過，無效的結算單位 (ERR_INVALID_SETTLEMENT_QUANTITY)。",
            }), 403

        # 高階密碼本不接受非正數數量：避免用負數數量「反向沖銷」直接換 FLAG。
        # 單價仍可在特權身分下覆寫（Parameter Tampering 為預期解法之一）。
        if product_id == "HU-PRD-027" and quantity < 1:
            return jsonify({
                "success": False,
                "message": "結算合約中斷：此資產不接受反向沖銷 (ERR_ASSET_FIXED_SETTLEMENT)。",
            }), 400

        # --- 業務邏輯漏洞 (Business Logic Flaw) ---
        total_cost = unit_price * quantity
        current_balance = session.get("balance", 0)

        # 餘額檢驗
        if current_balance < total_cost:
            return jsonify({
                "success": False,
                "message": f"餘額不足！採購需要 {total_cost:,} BTC，但您目前帳戶僅有 {current_balance:,} BTC。",
                "balance": current_balance,
            }), 400

        # 扣款（若 total_cost 為負數，扣除負數等於增加餘額）
        current_balance -= total_cost
        session["balance"] = current_balance

        # 成功採購目標商品：高階密碼本（HU-PRD-027）
        is_target_flag_item = (product_id == "HU-PRD-027")
        flag = FLAG_2 if is_target_flag_item else None

        if is_target_flag_item:
            msg = "採購成功！解密酬載已生成。"
        elif total_cost < 0:
            msg = f"【反向結算】黑市帳戶已套現退款 {-total_cost:,} BTC，最新餘額為 {current_balance:,} BTC。"
        else:
            msg = f"【採購成功】已扣除 {total_cost:,} BTC，[{product['name']}] 交付佇列已完成排程。"

        return jsonify({
            "success": True,
            "message": msg,
            "flag": flag,
            "balance": current_balance,
            "product_id": product_id,
            "product_name": product["name"],
            "order_id": f"HU-ORD-2026-{abs(hash(product_id + str(current_balance))) % 90000 + 10000}",
        })

    # 重設帳戶餘額端點（供測試與重新挑戰時使用）
    @website_bp.post("/api/reset-balance")
    @login_required
    def api_reset_balance():
        session["balance"] = 0
        return jsonify({"success": True, "balance": 0, "message": "帳戶 BTC 餘額已重設為 0。"})

    return website_bp