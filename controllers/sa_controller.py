from flask import Blueprint, render_template
from utils.auth import login_required

systemadmin_bp = Blueprint("systemadmin", __name__, url_prefix="/systemadmin")

# Dashboard
@systemadmin_bp.route("/index")
@login_required
def index():
    return render_template("systemadmin/index.html")