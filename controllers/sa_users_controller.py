from flask import Blueprint, render_template, request, redirect, url_for, flash
from utils.db import mongo
from utils.auth import login_required
from bson import ObjectId
from datetime import datetime
from werkzeug.security import generate_password_hash

users_bp = Blueprint("users", __name__, url_prefix="/systemadmin/users")


# -----------------------------
# VIEW USERS
# -----------------------------
@users_bp.route("/viewusers")
@login_required
def view_users():
    try:
        users = list(mongo.db.users.find())
        for u in users:
            u["_id"] = str(u["_id"])

            # Get related role and institute names
            u["role_name"] = "-"
            u["institute_name"] = "-"

            if u.get("role_id"):
                role = mongo.db.roles.find_one({"_id": ObjectId(u["role_id"])})
                if role:
                    u["role_name"] = role.get("name", "-")

            if u.get("institute_id"):
                inst = mongo.db.institute.find_one({"_id": ObjectId(u["institute_id"])})
                if inst:
                    u["institute_name"] = inst.get("name", "-")

        return render_template("systemadmin/viewUser.html", users=users)

    except Exception as e:
        flash(f"Error fetching users: {e}", "danger")
        return render_template("systemadmin/viewUser.html", users=[])


# -----------------------------
# ADD USER
# -----------------------------
@users_bp.route("/adduser", methods=["GET", "POST"])
@login_required
def add_user():
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        phone = request.form.get("phone")
        password = request.form.get("password")
        role_id = request.form.get("role_id")
        institute_id = request.form.get("institute_id")
        department = request.form.get("department")
        designation = request.form.get("designation")
        status = request.form.get("status", "Active")

        if not name or not email or not password:
            flash("Name, email, and password are required.", "warning")
            return redirect(url_for("users.add_user"))

        # Prevent duplicate users
        existing_user = mongo.db.users.find_one({"email": email})
        if existing_user:
            flash("User with this email already exists.", "danger")
            return redirect(url_for("users.add_user"))

        mongo.db.users.insert_one({
            "name": name,
            "email": email,
            "phone": phone,
            "password": generate_password_hash(password),
            "role_id": ObjectId(role_id) if role_id else None,
            "institute_id": ObjectId(institute_id) if institute_id else None,
            "department": department,
            "designation": designation,
            "status": status,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        })

        flash("User added successfully!", "success")
        return redirect(url_for("users.view_users"))

    # Fetch dropdown data
    roles = list(mongo.db.roles.find())
    institutes = list(mongo.db.institute.find())
    return render_template("systemadmin/manageUsers.html", user=None, roles=roles, institutes=institutes)


# -----------------------------
# EDIT USER
# -----------------------------
@users_bp.route("/edituser/<user_id>", methods=["GET", "POST"])
@login_required
def edit_user(user_id):
    user = mongo.db.users.find_one({"_id": ObjectId(user_id)})

    if not user:
        flash("User not found!", "danger")
        return redirect(url_for("users.view_users"))

    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        phone = request.form.get("phone")
        password = request.form.get("password")
        role_id = request.form.get("role_id")
        institute_id = request.form.get("institute_id")
        department = request.form.get("department")
        designation = request.form.get("designation")
        status = request.form.get("status", "Active")

        update_data = {
            "name": name,
            "email": email,
            "phone": phone,
            "role_id": ObjectId(role_id) if role_id else None,
            "institute_id": ObjectId(institute_id) if institute_id else None,
            "department": department,
            "designation": designation,
            "status": status,
            "updated_at": datetime.utcnow()
        }

        # Update password only if provided
        if password:
            update_data["password"] = generate_password_hash(password)

        mongo.db.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": update_data}
        )

        flash("User updated successfully!", "success")
        return redirect(url_for("users.view_users"))

    user["_id"] = str(user["_id"])
    roles = list(mongo.db.roles.find())
    institutes = list(mongo.db.institute.find())

    return render_template("systemadmin/manageUsers.html", user=user, roles=roles, institutes=institutes)


# -----------------------------
# DELETE USER
# -----------------------------
@users_bp.route("/deleteuser/<user_id>")
@login_required
def delete_user(user_id):
    try:
        user = mongo.db.users.find_one({"_id": ObjectId(user_id)})

        if not user:
            flash("User not found!", "danger")
            return redirect(url_for("users.view_users"))

        mongo.db.users.delete_one({"_id": ObjectId(user_id)})
        flash("User deleted successfully!", "success")

    except Exception as e:
        flash(f"Error deleting user: {e}", "danger")

    return redirect(url_for("users.view_users"))
