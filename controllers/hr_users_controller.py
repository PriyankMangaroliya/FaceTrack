from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from bson import ObjectId
from datetime import datetime
from utils.db import mongo
from utils.auth import login_required
from werkzeug.security import generate_password_hash

hr_users_bp = Blueprint("hr_users", __name__, url_prefix="/hr/users")


# View all HR users in the same institute
@hr_users_bp.route("/viewusers")
@login_required
def view_users():
    try:
        hr_user_id = session.get("user_id")
        if not hr_user_id:
            flash("Please log in first.", "warning")
            return redirect(url_for("auth.login"))

        # Fetch HR’s own data
        hr_user = mongo.db.users.find_one({"_id": ObjectId(hr_user_id)})
        if not hr_user:
            flash("HR account not found.", "danger")
            return redirect(url_for("auth.login"))

        institute_id = hr_user.get("institute_id")
        if not institute_id:
            flash("You are not assigned to any institute.", "danger")
            return render_template("hr/viewUsers.html", users=[])

        # Get role_id for "HR"
        hr_role = mongo.db.roles.find_one({"name": "HR"})
        if not hr_role:
            flash("HR role not found in the database.", "danger")
            return render_template("hr/viewUsers.html", users=[])

        # Fetch all HRs from the same institute
        users = list(mongo.db.users.find({
            "institute_id": ObjectId(institute_id),
            "role_id": hr_role["_id"]
        }))

        for user in users:
            user["_id"] = str(user["_id"])
            user["institute_name"] = mongo.db.institute.find_one(
                {"_id": ObjectId(institute_id)},
                {"name": 1}
            )["name"]

        return render_template("hr/viewUsers.html", users=users)

    except Exception as e:
        flash(f"Error fetching HR users: {e}", "danger")
        return render_template("hr/viewUsers.html", users=[])


# Add new HR user
@hr_users_bp.route("/adduser", methods=["GET", "POST"])
@login_required
def add_user():
    try:
        hr_user_id = session.get("user_id")
        hr_user = mongo.db.users.find_one({"_id": ObjectId(hr_user_id)})
        institute_id = hr_user.get("institute_id")

        if request.method == "POST":
            name = request.form.get("name")
            email = request.form.get("email")
            phone = request.form.get("phone")
            password = request.form.get("password")

            if not name or not email or not password:
                flash("All required fields must be filled.", "warning")
                return redirect(url_for("hr_users.add_user"))

            # Find HR role
            hr_role = mongo.db.roles.find_one({"name": "HR"})
            if not hr_role:
                flash("HR role not found in the database.", "danger")
                return redirect(url_for("hr_users.add_user"))

            # Check if user already exists
            existing_user = mongo.db.users.find_one({"email": email})
            if existing_user:
                flash("User with this email already exists!", "warning")
                return redirect(url_for("hr_users.add_user"))

            # Insert HR user
            mongo.db.users.insert_one({
                "name": name,
                "email": email,
                "phone": phone,
                "password": generate_password_hash(password),
                "role_id": hr_role["_id"],
                "institute_id": ObjectId(institute_id),
                "status": "Active",
                "created_at": datetime.utcnow()
            })

            flash("HR User added successfully!", "success")
            return redirect(url_for("hr_users.view_users"))

        return render_template("hr/manageUsers.html", user=None)

    except Exception as e:
        flash(f"Error adding HR user: {e}", "danger")
        return redirect(url_for("hr_users.view_users"))


# Update existing HR user
@hr_users_bp.route("/edituser/<user_id>", methods=["GET", "POST"])
@login_required
def edit_user(user_id):
    try:
        user = mongo.db.users.find_one({"_id": ObjectId(user_id)})
        if not user:
            flash("User not found!", "danger")
            return redirect(url_for("hr_users.view_users"))

        if request.method == "POST":
            name = request.form.get("name")
            email = request.form.get("email")
            phone = request.form.get("phone")
            status = request.form.get("status")

            mongo.db.users.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": {
                    "name": name,
                    "email": email,
                    "phone": phone,
                    "status": status,
                    "updated_at": datetime.utcnow()
                }}
            )

            flash("HR User updated successfully!", "success")
            return redirect(url_for("hr_users.view_users"))

        return render_template("hr/manageUsers.html", user=user)

    except Exception as e:
        flash(f"Error updating user: {e}", "danger")
        return redirect(url_for("hr_users.view_users"))


# Delete HR user
@hr_users_bp.route("/deleteuser/<user_id>")
@login_required
def delete_user(user_id):
    try:
        mongo.db.users.delete_one({"_id": ObjectId(user_id)})
        flash("HR User deleted successfully!", "success")
    except Exception as e:
        flash(f"Error deleting HR user: {e}", "danger")

    return redirect(url_for("hr_users.view_users"))
