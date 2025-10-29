from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from bson import ObjectId
from datetime import datetime
from utils.db import mongo
from utils.auth import login_required
from werkzeug.security import generate_password_hash

hr_users_bp = Blueprint("hr_users", __name__, url_prefix="/hr/users")


# VIEW ALL HR USERS (in same institute)
@hr_users_bp.route("/viewusers")
@login_required
def view_users():
    try:
        hr_user_id = session.get("user_id")
        if not hr_user_id:
            flash("Please log in first.", "warning")
            return redirect(url_for("auth.login"))

        hr_user = mongo.db.users.find_one({"_id": ObjectId(hr_user_id)})
        if not hr_user:
            flash("HR account not found.", "danger")
            return redirect(url_for("auth.login"))

        institute_id = hr_user.get("institute_id")
        if not institute_id:
            flash("You are not assigned to any institute.", "danger")
            return render_template("hr/viewUsers.html", users=[])

        hr_role = mongo.db.roles.find_one({"name": "HR"})
        if not hr_role:
            flash("HR role not found in the database.", "danger")
            return render_template("hr/viewUsers.html", users=[])

        users = list(mongo.db.users.find({
            "institute_id": ObjectId(institute_id),
            "role_id": hr_role["_id"]
        }))

        for user in users:
            user["_id"] = str(user["_id"])
            institute = mongo.db.institute.find_one({"_id": ObjectId(institute_id)}, {"name": 1})
            user["institute_name"] = institute.get("name", "-") if institute else "-"
            user["role_name"] = "HR"

        return render_template("hr/viewUsers.html", users=users)

    except Exception as e:
        flash(f"Error fetching HR users: {e}", "danger")
        return render_template("hr/viewUsers.html", users=[])


# ADD HR USER
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
            department = request.form.get("department")
            designation = request.form.get("designation")

            if not name or not email or not password:
                flash("Name, Email, and Password are required.", "warning")
                return redirect(url_for("hr_users.add_user"))

            hr_role = mongo.db.roles.find_one({"name": "HR"})
            if not hr_role:
                flash("HR role not found.", "danger")
                return redirect(url_for("hr_users.add_user"))

            if mongo.db.users.find_one({"email": email}):
                flash("User with this email already exists.", "warning")
                return redirect(url_for("hr_users.add_user"))

            mongo.db.users.insert_one({
                "name": name,
                "email": email,
                "phone": phone,
                "password": generate_password_hash(password),
                "role_id": hr_role["_id"],
                "institute_id": ObjectId(institute_id),
                "department": department,
                "designation": designation,
                "status": "Active",
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            })

            flash("HR user added successfully!", "success")
            return redirect(url_for("hr_users.view_users"))

        return render_template("hr/manageUsers.html", user=None)

    except Exception as e:
        flash(f"Error adding HR user: {e}", "danger")
        return redirect(url_for("hr_users.view_users"))


# UPDATE HR USER
@hr_users_bp.route("/edituser/<user_id>", methods=["GET", "POST"])
@login_required
def edit_user(user_id):
    try:
        user = mongo.db.users.find_one({"_id": ObjectId(user_id)})
        if not user:
            flash("User not found.", "danger")
            return redirect(url_for("hr_users.view_users"))

        if request.method == "POST":
            name = request.form.get("name")
            email = request.form.get("email")
            phone = request.form.get("phone")
            department = request.form.get("department")
            designation = request.form.get("designation")
            status = request.form.get("status")

            mongo.db.users.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": {
                    "name": name,
                    "email": email,
                    "phone": phone,
                    "department": department,
                    "designation": designation,
                    "status": status,
                    "updated_at": datetime.utcnow()
                }}
            )

            flash("HR user updated successfully!", "success")
            return redirect(url_for("hr_users.view_users"))

        user["_id"] = str(user["_id"])
        return render_template("hr/manageUsers.html", user=user)

    except Exception as e:
        flash(f"Error updating HR user: {e}", "danger")
        return redirect(url_for("hr_users.view_users"))


# DELETE HR USER
@hr_users_bp.route("/deleteuser/<user_id>")
@login_required
def delete_user(user_id):
    try:
        mongo.db.users.delete_one({"_id": ObjectId(user_id)})
        flash("HR user deleted successfully!", "success")
    except Exception as e:
        flash(f"Error deleting HR user: {e}", "danger")

    return redirect(url_for("hr_users.view_users"))
