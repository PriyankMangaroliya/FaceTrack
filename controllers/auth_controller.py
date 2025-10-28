from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from models.users import User
from utils.auth import logout_user

auth_bp = Blueprint("auth", __name__)

# Login
@auth_bp.route("/", methods=["GET", "POST"])
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


# Logout
@auth_bp.route("/logout")
def logout():
    return logout_user()


# View Profile
@auth_bp.route("/profile")
def view_profile():
    from bson import ObjectId
    from utils.db import mongo

    user_id = session.get("user_id")
    if not user_id:
        flash("Please log in to view your profile.", "warning")
        return redirect(url_for("auth.login"))

    # Fetch user data
    user = mongo.db.users.find_one({"_id": ObjectId(user_id)})

    if not user:
        flash("User not found!", "danger")
        return redirect(url_for("auth.login"))

    # Convert ObjectIds for role and institute to readable names
    role = mongo.db.roles.find_one({"_id": user.get("role_id")}) if user.get("role_id") else None
    institute = mongo.db.institute.find_one({"_id": user.get("institute_id")}) if user.get("institute_id") else None

    return render_template(
        "auth-profile.html",
        user=user,
        role=role,
        institute=institute
    )
