from flask import Blueprint, render_template

systemadmin_bp = Blueprint("systemadmin", __name__, url_prefix="/systemadmin")

@systemadmin_bp.route("/index")
def index():
    return render_template("systemadmin/index.html")
