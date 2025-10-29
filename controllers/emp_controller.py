from flask import Blueprint, render_template
from utils.auth import login_required

employee_bp = Blueprint("employee", __name__, url_prefix="/employee")

# Dashboard
@employee_bp.route("/index")
@login_required
def index():
    return render_template("employee/index.html")