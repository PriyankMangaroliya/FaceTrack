from flask import Blueprint, render_template
from utils.auth import login_required

hr_bp = Blueprint("hr", __name__, url_prefix="/hr")

# Dashboard
@hr_bp.route("/index")
@login_required
def index():
    return render_template("hr/index.html")