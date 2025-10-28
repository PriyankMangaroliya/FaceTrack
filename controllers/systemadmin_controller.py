from flask import Blueprint, render_template
from utils.auth import login_required  # import decorator

systemadmin_bp = Blueprint("systemadmin", __name__, url_prefix="/systemadmin")

@systemadmin_bp.route("/index")
@login_required
def index():
    return render_template("systemadmin/index.html")


@systemadmin_bp.route("/viewroles")
@login_required
def viewroles():
    return render_template("systemadmin/viewRole.html")
