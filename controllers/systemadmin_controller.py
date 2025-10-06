from flask import Blueprint, render_template
from utils.auth import login_required  # import decorator

systemadmin_bp = Blueprint("systemadmin", __name__, url_prefix="/systemadmin")

@login_required
@systemadmin_bp.route("/index")
def index():
    return render_template("systemadmin/index.html")
