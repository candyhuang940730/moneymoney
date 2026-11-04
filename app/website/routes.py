from flask import Blueprint, render_template

website_bp = Blueprint("website", __name__, url_prefix="/site")


@website_bp.get("/")
def index():
    return render_template("website/login.html")

