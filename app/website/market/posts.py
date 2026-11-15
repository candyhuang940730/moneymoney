import os
import sqlite3
from io import BytesIO
from pathlib import Path
from uuid import uuid4
from contextlib import closing

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    abort,
    current_app,
    send_from_directory,
)
from PIL import Image, ImageOps, UnidentifiedImageError

posts_bp = Blueprint("posts", __name__, url_prefix="/site/posts")

MAX_IMAGE_SIZE = 3 * 1024 * 1024
MAX_IMAGE_PIXELS = 12_000_000
Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS

CATEGORIES = ["電子產品", "服飾配件", "生活用品", "遊戲娛樂", "收藏商品", "其他"]

STATUSES = {"active": "上架中", "inactive": "已下架", "draft": "草稿"}


# =================================
# SQLite 資料庫
# =================================


def get_db():
    folder = Path(current_app.instance_path)
    folder.mkdir(parents=True, exist_ok=True)

    db_path = folder / "seller_posts.sqlite3"

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    conn.execute("""
        CREATE TABLE IF NOT EXISTS seller_posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            author TEXT NOT NULL,
            image_filename TEXT,
            price INTEGER NOT NULL DEFAULT 0,
            category TEXT NOT NULL DEFAULT '其他',
            status TEXT NOT NULL DEFAULT 'active',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    columns = {row["name"] for row in conn.execute("PRAGMA table_info(seller_posts)")}

    # 舊資料庫自動新增欄位
    if "image_filename" not in columns:
        conn.execute("""
            ALTER TABLE seller_posts
            ADD COLUMN image_filename TEXT
        """)

    if "price" not in columns:
        conn.execute("""
            ALTER TABLE seller_posts
            ADD COLUMN price INTEGER NOT NULL DEFAULT 0
        """)

    if "category" not in columns:
        conn.execute("""
            ALTER TABLE seller_posts
            ADD COLUMN category TEXT NOT NULL DEFAULT '其他'
        """)

    if "status" not in columns:
        conn.execute("""
            ALTER TABLE seller_posts
            ADD COLUMN status TEXT NOT NULL DEFAULT 'active'
        """)

    conn.commit()

    return conn


# =================================
# 商品資料驗證
# =================================


def get_product_fields():
    price_text = request.form.get("price", "").strip()
    category = request.form.get("category", "").strip()
    status = request.form.get("status", "active").strip()

    try:
        price = int(price_text)
    except ValueError:
        abort(400, description="請輸入正確的整數價格")

    if price < 0 or price > 100000000:
        abort(400, description="商品價格超出允許範圍")

    if category not in CATEGORIES:
        abort(400, description="請選擇有效的商品分類")

    if status not in STATUSES:
        abort(400, description="無效的商品狀態")

    return price, category, status


# =================================
# 商品圖片
# =================================


def upload_folder():
    folder = Path(current_app.instance_path) / "seller_uploads"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def save_image(file):
    if file is None or not file.filename:
        return None

    data = file.stream.read(MAX_IMAGE_SIZE + 1)

    if len(data) > MAX_IMAGE_SIZE:
        abort(400, description="圖片不可超過 3 MB")

    try:
        with Image.open(BytesIO(data)) as img:
            if img.format not in ("JPEG", "PNG", "WEBP"):
                abort(400, description="只支援 JPG、PNG、WebP 圖片")

            if img.width * img.height > MAX_IMAGE_PIXELS:
                abort(400, description="圖片解析度過大")

            img = ImageOps.exif_transpose(img)
            img.thumbnail((1600, 1600))

            # 統一輸出成 JPEG
            # 避免直接儲存使用者原始檔案
            if img.mode in ("RGBA", "LA"):
                rgba = img.convert("RGBA")
                background = Image.new("RGB", rgba.size, (255, 255, 255))
                background.paste(rgba, mask=rgba.getchannel("A"))
                img = background
            else:
                img = img.convert("RGB")

            filename = f"{uuid4().hex}.jpg"
            path = upload_folder() / filename

            img.save(path, format="JPEG", quality=85)

            return filename

    except (
        UnidentifiedImageError,
        OSError,
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
    ):
        abort(400, description="圖片格式不正確")


def remove_image(filename):
    if not filename:
        return

    path = upload_folder() / Path(filename).name
    path.unlink(missing_ok=True)


# =================================
# 貼文列表
# =================================


# 公開商品列表：只顯示上架商品
@posts_bp.route("/")
def post_list():
    with closing(get_db()) as conn:
        rows = conn.execute("""
            SELECT *
            FROM seller_posts
            WHERE status = 'active'
            ORDER BY id DESC
        """).fetchall()

    return render_template("website/posts/list.html", posts=[dict(row) for row in rows])


# =================================
# 新增貼文
# =================================


@posts_bp.route("/create", methods=["GET", "POST"])
def create_post():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        content = request.form.get("content", "").strip()

        if not title or not content:
            abort(400, description="標題和內容不可空白")

        if len(title) > 100:
            abort(400, description="標題不可超過100字")

        price, category, status = get_product_fields()

        image_filename = save_image(request.files.get("image"))

        # 目前為測試賣家
        # 之後再整合組員的登入系統
        author = "seller01"

        try:
            with closing(get_db()) as conn:
                conn.execute(
                    """
                    INSERT INTO seller_posts
                    (
                        title,
                        content,
                        author,
                        image_filename,
                        price,
                        category,
                        status
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                    (title, content, author, image_filename, price, category, status),
                )
                conn.commit()
        except Exception:
            remove_image(image_filename)
            raise

        return redirect(url_for("posts.post_list"))

    return render_template(
        "website/posts/create.html", categories=CATEGORIES, statuses=STATUSES
    )


# =================================
# 文章詳情
# =================================


# 公開商品詳情：只允許查看上架商品
@posts_bp.route("/<int:post_id>")
def post_detail(post_id):
    with closing(get_db()) as conn:
        row = conn.execute(
            """
            SELECT *
            FROM seller_posts
            WHERE id = ? AND status = 'active'
        """,
            (post_id,),
        ).fetchone()

    if row is None:
        abort(404)

    return render_template(
        "website/posts/detail.html", post=dict(row), is_seller_preview=False
    )


# =================================
# 顯示圖片
# =================================


@posts_bp.route("/<int:post_id>/image")
def post_image(post_id):
    with closing(get_db()) as conn:
        row = conn.execute(
            """
            SELECT image_filename
            FROM seller_posts
            WHERE id = ?
        """,
            (post_id,),
        ).fetchone()

    if row is None or not row["image_filename"]:
        abort(404)

    return send_from_directory(
        upload_folder(), row["image_filename"], mimetype="image/jpeg"
    )


# =================================
# 編輯貼文
# =================================


@posts_bp.route("/<int:post_id>/edit", methods=["GET", "POST"])
def edit_post(post_id):
    with closing(get_db()) as conn:
        row = conn.execute(
            """
            SELECT *
            FROM seller_posts
            WHERE id = ?
        """,
            (post_id,),
        ).fetchone()

    if row is None:
        abort(404)

    post = dict(row)

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        content = request.form.get("content", "").strip()

        if not title or not content:
            abort(400, description="標題和內容不可空白")

        if len(title) > 100:
            abort(400, description="標題不可超過100字")

        price, category, status = get_product_fields()

        new_image = save_image(request.files.get("image"))

        image_filename = new_image or post["image_filename"]

        try:
            with closing(get_db()) as conn:
                conn.execute(
                    """
                    UPDATE seller_posts
                    SET title = ?,
                        content = ?,
                        image_filename = ?,
                        price = ?,
                        category = ?,
                        status = ?
                    WHERE id = ?
                """,
                    (title, content, image_filename, price, category, status, post_id),
                )
                conn.commit()
        except Exception:
            remove_image(new_image)
            raise

        if new_image:
            remove_image(post["image_filename"])

        return redirect(url_for("posts.seller_preview", post_id=post_id))

    return render_template(
        "website/posts/edit.html", post=post, categories=CATEGORIES, statuses=STATUSES
    )


# =================================
# 刪除貼文
# =================================


@posts_bp.route("/<int:post_id>/delete", methods=["POST"])
def delete_post(post_id):
    with closing(get_db()) as conn:
        row = conn.execute(
            """
            SELECT image_filename
            FROM seller_posts
            WHERE id = ?
        """,
            (post_id,),
        ).fetchone()

        if row is None:
            abort(404)

        conn.execute(
            """
            DELETE FROM seller_posts
            WHERE id = ?
        """,
            (post_id,),
        )
        conn.commit()

    remove_image(row["image_filename"])

    return redirect(url_for("posts.post_list"))


# =================================
# 賣家管理中心 Dashboard
# =================================


# =================================
# Seller Dashboard：搜尋、排序、狀態篩選
# =================================


# =================================
# Seller Dashboard：搜尋、排序、分頁
# =================================


@posts_bp.route("/dashboard")
def seller_dashboard():
    seller = "seller01"  # 本機測試用

    keyword = request.args.get("q", "").strip()[:100]
    selected_status = request.args.get("status", "all")
    selected_sort = request.args.get("sort", "newest")

    if selected_status not in {"all", "active", "inactive", "draft"}:
        selected_status = "all"

    sort_options = {
        "newest": "id DESC",
        "oldest": "id ASC",
        "price_high": "price DESC, id DESC",
        "price_low": "price ASC, id DESC",
    }

    if selected_sort not in sort_options:
        selected_sort = "newest"

    # 每頁顯示 5 筆商品
    per_page = 5

    try:
        page = int(request.args.get("page", "1"))
    except ValueError:
        page = 1

    page = max(page, 1)

    with closing(get_db()) as conn:

        # 統計全部狀態的商品
        count_rows = conn.execute(
            """
            SELECT status, COUNT(*) AS total
            FROM seller_posts
            WHERE author = ?
            GROUP BY status
        """,
            (seller,),
        ).fetchall()

        counts = {"all": 0, "active": 0, "inactive": 0, "draft": 0}

        for row in count_rows:
            if row["status"] in counts:
                counts[row["status"]] = row["total"]
                counts["all"] += row["total"]

        # 搜尋與篩選條件
        conditions = ["author = ?"]
        parameters = [seller]

        if selected_status != "all":
            conditions.append("status = ?")
            parameters.append(selected_status)

        if keyword:
            conditions.append("(title LIKE ? OR content LIKE ?)")
            pattern = f"%{keyword}%"
            parameters.extend([pattern, pattern])

        where_clause = " AND ".join(conditions)

        # 計算符合條件的商品總數
        total = conn.execute(
            f"""
            SELECT COUNT(*)
            FROM seller_posts
            WHERE {where_clause}
            """,
            parameters,
        ).fetchone()[0]

        total_pages = max(1, (total + per_page - 1) // per_page)

        # 避免超出最後一頁
        page = min(page, total_pages)

        offset = (page - 1) * per_page

        # 只讀取當前頁面的資料
        sql = f"""
            SELECT *
            FROM seller_posts
            WHERE {where_clause}
            ORDER BY {sort_options[selected_sort]}
            LIMIT ? OFFSET ?
        """

        rows = conn.execute(sql, [*parameters, per_page, offset]).fetchall()

    return render_template(
        "website/posts/dashboard.html",
        posts=[dict(row) for row in rows],
        counts=counts,
        seller=seller,
        keyword=keyword,
        selected_status=selected_status,
        selected_sort=selected_sort,
        page=page,
        total_pages=total_pages,
        total=total,
    )


# =================================
# 賣家商品預覽（本機測試）
# =================================


@posts_bp.route("/dashboard/preview/<int:post_id>")
def seller_preview(post_id):
    seller = "seller01"

    with closing(get_db()) as conn:
        row = conn.execute(
            """
            SELECT *
            FROM seller_posts
            WHERE id = ? AND author = ?
        """,
            (post_id, seller),
        ).fetchone()

    if row is None:
        abort(404)

    return render_template(
        "website/posts/detail.html", post=dict(row), is_seller_preview=True
    )


# =================================
# 快速上架 / 下架（本機測試）
# =================================


@posts_bp.route("/<int:post_id>/toggle-status", methods=["POST"])
def toggle_post_status(post_id):
    seller = "seller01"

    with closing(get_db()) as conn:
        row = conn.execute(
            """
            SELECT status
            FROM seller_posts
            WHERE id = ? AND author = ?
        """,
            (post_id, seller),
        ).fetchone()

        if row is None:
            abort(404)

        if row["status"] == "draft":
            abort(400, description="請先編輯草稿")

        new_status = "inactive" if row["status"] == "active" else "active"

        conn.execute(
            """
            UPDATE seller_posts
            SET status = ?
            WHERE id = ? AND author = ?
        """,
            (new_status, post_id, seller),
        )

        conn.commit()

    return redirect(url_for("posts.seller_dashboard"))


# ==========================================
# HYDRA CTF - IDOR 私人貼文挑戰
# 僅供本機教學測試
# ==========================================

def setup_idor_posts(conn):
    # 獨立的 CTF 資料表，不影響正常商品
    conn.execute("""
        CREATE TABLE IF NOT EXISTS seller_ctf_idor_posts (
            id INTEGER PRIMARY KEY,
            author TEXT NOT NULL,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            status TEXT NOT NULL
        )
    """)

    demo_posts = [
        (
            1,
            "seller01",
            "進貨紀錄",
            "這是我的私人進貨紀錄。",
            "draft"
        ),
        (
            2,
            "seller01",
            "未公開的交易情報",
            "這篇貼文還沒有公開。",
            "draft"
        ),
        (
            3,
            "seller02",
            "機密交易情報",
            "這是其他賣家的機密資料。",
            "draft"
        )
    ]

    conn.executemany("""
        INSERT OR IGNORE INTO seller_ctf_idor_posts
        (id, author, title, content, status)
        VALUES (?, ?, ?, ?, ?)
    """, demo_posts)

    flag = os.environ.get("SELLER_IDOR_FLAG")

    if not flag:
        abort(503, description="尚未設定 IDOR Flag")

    # 將 Flag 放在 seller02 的私人草稿
    conn.execute("""
        UPDATE seller_ctf_idor_posts
        SET content = ?
        WHERE id = 3 AND author = 'seller02'
    """, (
        "這是 seller02 的私人機密情報。\n"
        "其他賣家禁止查看。\n\n"
        f"FLAG: {flag}",
    ))

    conn.commit()


@posts_bp.route("/ctf/idor")
@posts_bp.route("/ctf/idor/<int:post_id>")
def seller_idor_challenge(post_id=None):

    # 僅允許明確啟用的本機測試環境
    if (
        os.environ.get("ENABLE_IDOR_LAB") != "1"
        or request.remote_addr not in ("127.0.0.1", "::1")
        or request.host not in (
            "127.0.0.1:5000",
            "localhost:5000"
        )
    ):
        abort(404)

    # 暫時模擬登入者 seller01
    current_seller = "seller01"

    with closing(get_db()) as conn:
        setup_idor_posts(conn)

        # 正常列表只顯示自己的貼文
        own_posts = conn.execute("""
            SELECT *
            FROM seller_ctf_idor_posts
            WHERE author = ?
            ORDER BY id
        """, (current_seller,)).fetchall()

        post = None

        if post_id is not None:

            # 故意留下的 IDOR 漏洞
            # 只檢查 ID，沒有驗證 author
            row = conn.execute("""
                SELECT *
                FROM seller_ctf_idor_posts
                WHERE id = ?
            """, (post_id,)).fetchone()

            if row is None:
                abort(404)

            post = dict(row)

    return render_template(
        "website/posts/ctf_idor.html",
        posts=[dict(row) for row in own_posts],
        post=post,
        current_seller=current_seller
    )
