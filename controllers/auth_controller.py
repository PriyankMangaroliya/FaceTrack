from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from models.users import User
from utils.auth import logout_user
from utils.db import mongo

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

            # Fetch role name from role_id (if stored separately)
            role = mongo.db.roles.find_one({"_id": user.get("role_id")})
            role_name = role["name"].lower() if role else "employee"

            flash(f"Welcome {user['name']}!", "success")

            # Redirect based on role
            if role_name == "system admin":
                return redirect(url_for("systemadmin.index"))
            elif role_name == "hr":
                return redirect(url_for("hr.index"))
            elif role_name == "employee":
                return redirect(url_for("employee.index"))
            else:
                # Default if role not found
                flash("Role not recognized. Redirecting to home.", "warning")
                return redirect(url_for("auth.login"))

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
