from flask import Blueprint, render_template

ctf_center_bp = Blueprint("ctf_center", __name__, url_prefix="/ctf")

CHAPTERS = (
    {"number": "01", "title": "初來乍到", "summary": "地下網路的入口與身分驗證"},
    {"number": "02", "title": "資本累積", "summary": "交易、市場與帳戶之間的線索"},
    {"number": "03", "title": "暗地通訊", "summary": "留言、舉報與管理操作"},
    {"number": "04", "title": "伺服器滲透", "summary": "上傳內容與內部服務"},
    {"number": "05", "title": "終極真相", "summary": "被封存的最後一份文件"},
)


@ctf_center_bp.get("/")
def index():
    return render_template("ctf_center/index.html", chapters=CHAPTERS)

