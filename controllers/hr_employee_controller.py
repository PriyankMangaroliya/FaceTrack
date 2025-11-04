from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from bson import ObjectId
from utils.db import mongo
from utils.auth import login_required
from werkzeug.security import generate_password_hash
from datetime import datetime
import os

# Import face utilities
from utils.face_utils import capture_faces_for_user, check_existing_faces

hr_employee_bp = Blueprint("employee_users", __name__, url_prefix="/hr/employee")


# -----------------------------
# VIEW EMPLOYEES (only Employee role)
# -----------------------------
@hr_employee_bp.route("/viewusers")
@login_required
def view_users():
    try:
        user_id = session.get("user_id")
        if not user_id:
            flash("Please log in first.", "warning")
            return redirect(url_for("auth.login"))

        current_user = mongo.db.users.find_one({"_id": ObjectId(user_id)})
        if not current_user:
            flash("User not found.", "danger")
            return redirect(url_for("auth.login"))

        institute_id = current_user.get("institute_id")
        employee_role = mongo.db.roles.find_one({"name": "Employee"})

        if not employee_role:
            flash("Employee role not found.", "danger")
            return render_template("hr/viewEmployees.html", users=[])

        users = list(mongo.db.users.find({
            "institute_id": ObjectId(institute_id),
            "role_id": ObjectId(employee_role["_id"])
        }))

        # Add display helpers
        for user in users:
            user["_id"] = str(user["_id"])
            user["face_registered"] = check_existing_faces(user["_id"], user["name"])
            user["role_name"] = "Employee"

        return render_template("hr/viewEmployees.html", users=users)

    except Exception as e:
        flash(f"Error fetching employees: {e}", "danger")
        return render_template("hr/viewEmployees.html", users=[])


# -----------------------------
# ADD EMPLOYEE
# -----------------------------
@hr_employee_bp.route("/adduser", methods=["GET", "POST"])
@login_required
def add_user():
    try:
        current_user_id = session.get("user_id")
        hr_user = mongo.db.users.find_one({"_id": ObjectId(current_user_id)})

        if request.method == "POST":
            name = request.form.get("name")
            email = request.form.get("email")
            phone = request.form.get("phone")
            password = request.form.get("password")
            department = request.form.get("department")
            designation = request.form.get("designation")
            status = request.form.get("status") or "Active"

            if not all([name, email, password]):
                flash("Name, email, and password are required.", "warning")
                return redirect(url_for("employee_users.add_user"))

            employee_role = mongo.db.roles.find_one({"name": "Employee"})
            if not employee_role:
                flash("Employee role not found!", "danger")
                return redirect(url_for("employee_users.add_user"))

            if mongo.db.users.find_one({"email": email}):
                flash("Email already registered!", "warning")
                return redirect(url_for("employee_users.add_user"))

            new_user = {
                "name": name,
                "email": email,
                "phone": phone,
                "password": generate_password_hash(password),
                "role_id": ObjectId(employee_role["_id"]),
                "institute_id": ObjectId(hr_user["institute_id"]),
                "department": department,
                "designation": designation,
                "status": status,
                "face_registered": False,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            }

            mongo.db.users.insert_one(new_user)
            flash("Employee added successfully!", "success")
            return redirect(url_for("employee_users.view_users"))

        return render_template("hr/manageEmployees.html", user=None)

    except Exception as e:
        flash(f"Error adding employee: {e}", "danger")
        return redirect(url_for("employee_users.view_users"))


# -----------------------------
# UPDATE EMPLOYEE
# -----------------------------
@hr_employee_bp.route("/edituser/<user_id>", methods=["GET", "POST"])
@login_required
def edit_user(user_id):
    try:
        user = mongo.db.users.find_one({"_id": ObjectId(user_id)})
        if not user:
            flash("Employee not found!", "danger")
            return redirect(url_for("employee_users.view_users"))

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

            flash("Employee updated successfully!", "success")
            return redirect(url_for("employee_users.view_users"))

        user["_id"] = str(user["_id"])
        return render_template("hr/manageEmployees.html", user=user)

    except Exception as e:
        flash(f"Error updating employee: {e}", "danger")
        return redirect(url_for("employee_users.view_users"))


# -----------------------------
# DELETE EMPLOYEE
# -----------------------------
@hr_employee_bp.route("/deleteuser/<user_id>")
@login_required
def delete_user(user_id):
    try:
        mongo.db.users.delete_one({"_id": ObjectId(user_id)})
        flash("Employee deleted successfully!", "success")
    except Exception as e:
        flash(f"Error deleting employee: {e}", "danger")

    return redirect(url_for("employee_users.view_users"))


# -----------------------------
# REGISTER FACE (NEW)
# -----------------------------
@hr_employee_bp.route("/register_face/<user_id>")
@login_required
def register_face(user_id):
    try:
        user = mongo.db.users.find_one({"_id": ObjectId(user_id)})
        if not user:
            flash("Employee not found!", "danger")
            return redirect(url_for("employee_users.view_users"))

        folder_path = capture_faces_for_user(user_id, user["name"])
        if folder_path:
            mongo.db.users.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": {"face_registered": True, "updated_at": datetime.utcnow()}}
            )
            flash("Face registered successfully!", "success")
        else:
            flash("No faces captured. Try again.", "warning")

    except Exception as e:
        flash(f"Error during face registration: {e}", "danger")

    return redirect(url_for("employee_users.view_users"))


# -----------------------------
# VIEW FACE (NEW)
# -----------------------------
@hr_employee_bp.route("/view_face/<user_id>")
@login_required
def view_face(user_id):
    try:
        user = mongo.db.users.find_one({"_id": ObjectId(user_id)})
        if not user:
            flash("Employee not found!", "danger")
            return redirect(url_for("employee_users.view_users"))

        dataset_path = os.path.join("dataset", f"{user_id}_{user['name']}")
        if not os.path.exists(dataset_path):
            flash("No face data found. Please register first.", "warning")
            return redirect(url_for("employee_users.view_users"))

        # List captured images for preview
        images = [f for f in os.listdir(dataset_path) if f.endswith(".jpg") or f.endswith(".png")]
        return render_template("hr/viewFace.html", user=user, images=images, folder=dataset_path)

    except Exception as e:
        flash(f"Error viewing face data: {e}", "danger")
        return redirect(url_for("employee_users.view_users"))
