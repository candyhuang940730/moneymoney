
import sqlite3
from io import BytesIO
from pathlib import Path
from uuid import uuid4
from contextlib import closing

from flask import (
    Blueprint, render_template, request,
    redirect, url_for, abort, current_app,
    send_from_directory
)
from PIL import Image, ImageOps, UnidentifiedImageError

posts_bp = Blueprint(
    "posts",
    __name__,
    url_prefix="/site/posts"
)

MAX_IMAGE_SIZE = 3 * 1024 * 1024
MAX_IMAGE_PIXELS = 12_000_000


# SQLite 資料庫
def get_db():
    folder = Path(current_app.instance_path)
    folder.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(folder / "seller_posts.sqlite3")
    conn.row_factory = sqlite3.Row

    conn.execute("""
        CREATE TABLE IF NOT EXISTS seller_posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            author TEXT NOT NULL,
            image_filename TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 舊版資料庫自動增加圖片欄位
    columns = {
        row["name"]
        for row in conn.execute("PRAGMA table_info(seller_posts)")
    }

    if "image_filename" not in columns:
        conn.execute("""
            ALTER TABLE seller_posts
            ADD COLUMN image_filename TEXT
        """)

    conn.commit()
    return conn


# 圖片儲存位置
def upload_folder():
    folder = Path(current_app.instance_path) / "seller_uploads"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


# 處理上傳圖片
def save_image(file):
    if file is None or not file.filename:
        return None

    data = file.stream.read(MAX_IMAGE_SIZE + 1)

    if len(data) > MAX_IMAGE_SIZE:
        abort(400, description="圖片不可超過 3 MB")

    try:
        with Image.open(BytesIO(data)) as img:
            if img.format not in ("JPEG", "PNG", "WEBP"):
                abort(400, description="只允許 JPG、PNG、WebP")

            if img.width * img.height > MAX_IMAGE_PIXELS:
                abort(400, description="圖片解析度過大")

            img = ImageOps.exif_transpose(img)
            img.thumbnail((1600, 1600))

            # 統一轉成 JPEG，移除原始檔內的額外資訊
            if img.mode in ("RGBA", "LA"):
                rgba = img.convert("RGBA")
                background = Image.new(
                    "RGB", rgba.size, (255, 255, 255)
                )
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
        Image.DecompressionBombError
    ):
        abort(400, description="圖片格式無效或檔案損壞")


# 刪除舊圖片
def remove_image(filename):
    if filename:
        path = upload_folder() / Path(filename).name
        path.unlink(missing_ok=True)


# 貼文列表
@posts_bp.route("/")
def post_list():
    with closing(get_db()) as conn:
        rows = conn.execute("""
            SELECT * FROM seller_posts
            ORDER BY id DESC
        """).fetchall()

    return render_template(
        "website/posts/list.html",
        posts=[dict(row) for row in rows]
    )


# 新增貼文
@posts_bp.route("/create", methods=["GET", "POST"])
def create_post():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        content = request.form.get("content", "").strip()

        if not title or not content:
            abort(400, description="標題和內容不能空白")

        if len(title) > 100:
            abort(400, description="標題不能超過100字")

        image_filename = save_image(
            request.files.get("image")
        )

        with closing(get_db()) as conn:
            conn.execute("""
                INSERT INTO seller_posts
                    (title, content, author, image_filename)
                VALUES (?, ?, ?, ?)
            """, (
                title, content, "seller01", image_filename
            ))
            conn.commit()

        return redirect(url_for("posts.post_list"))

    return render_template("website/posts/create.html")


# 文章詳情
@posts_bp.route("/<int:post_id>")
def post_detail(post_id):
    with closing(get_db()) as conn:
        row = conn.execute(
            "SELECT * FROM seller_posts WHERE id = ?",
            (post_id,)
        ).fetchone()

    if row is None:
        abort(404)

    return render_template(
        "website/posts/detail.html",
        post=dict(row)
    )


# 顯示文章圖片
@posts_bp.route("/<int:post_id>/image")
def post_image(post_id):
    with closing(get_db()) as conn:
        row = conn.execute("""
            SELECT image_filename FROM seller_posts
            WHERE id = ?
        """, (post_id,)).fetchone()

    if row is None or not row["image_filename"]:
        abort(404)

    return send_from_directory(
        upload_folder(),
        row["image_filename"],
        mimetype="image/jpeg"
    )


# 編輯貼文
@posts_bp.route(
    "/<int:post_id>/edit",
    methods=["GET", "POST"]
)
def edit_post(post_id):
    with closing(get_db()) as conn:
        row = conn.execute(
            "SELECT * FROM seller_posts WHERE id = ?",
            (post_id,)
        ).fetchone()

    if row is None:
        abort(404)

    post = dict(row)

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        content = request.form.get("content", "").strip()

        if not title or not content:
            abort(400, description="標題和內容不能空白")

        if len(title) > 100:
            abort(400, description="標題不能超過100字")

        new_image = save_image(
            request.files.get("image")
        )

        image_filename = (
            new_image or post["image_filename"]
        )

        with closing(get_db()) as conn:
            conn.execute("""
                UPDATE seller_posts
                SET title = ?, content = ?, image_filename = ?
                WHERE id = ?
            """, (
                title, content, image_filename, post_id
            ))
            conn.commit()

        if new_image:
            remove_image(post["image_filename"])

        return redirect(
            url_for("posts.post_detail", post_id=post_id)
        )

    return render_template(
        "website/posts/edit.html",
        post=post
    )


# 刪除貼文
@posts_bp.route(
    "/<int:post_id>/delete",
    methods=["POST"]
)
def delete_post(post_id):
    with closing(get_db()) as conn:
        row = conn.execute(
            "SELECT image_filename FROM seller_posts WHERE id = ?",
            (post_id,)
        ).fetchone()

        if row is None:
            abort(404)

        conn.execute(
            "DELETE FROM seller_posts WHERE id = ?",
            (post_id,)
        )
        conn.commit()

    remove_image(row["image_filename"])

    return redirect(url_for("posts.post_list"))
