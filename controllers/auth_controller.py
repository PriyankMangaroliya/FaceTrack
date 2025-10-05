from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from models.users import User

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        user = User.verify_password(email, password)
        if user:
            # Save user info in session
            session["user_id"] = str(user["_id"])
            session["user_name"] = user["name"]

            flash(f"Welcome {user['name']}!", "success")

            return redirect(url_for("systemadmin.index"))

        else:
            flash("Invalid email or password", "danger")
            return redirect(url_for("auth.login"))

    return render_template("auth-login.html")
