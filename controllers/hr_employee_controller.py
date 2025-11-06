from flask import Blueprint, render_template, request, redirect, url_for, flash, session, Response
from bson import ObjectId
from utils.db import mongo
from utils.auth import login_required
from werkzeug.security import generate_password_hash
from datetime import datetime

# Import face utilities
from utils.face_utils import capture_faces_for_user, is_face_registered, generate_camera_frames

hr_employee_bp = Blueprint("employee_users", __name__, url_prefix="/hr/employee")


# -------------------------------------------------------------
# VIEW EMPLOYEES (only Employee role)
# -------------------------------------------------------------
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
            flash("User not found!", "danger")
            return redirect(url_for("auth.login"))

        institute_id = current_user.get("institute_id")
        employee_role = mongo.db.roles.find_one({"name": "Employee"})
        if not employee_role:
            flash("Employee role not found.", "danger")
            return render_template("hr/viewEmployees.html", users=[])

        users = list(mongo.db.users.find({
            "institute_id": ObjectId(institute_id),
            "role_id": ObjectId(employee_role["_id"])
        }).sort("name", 1))

        # Attach button info for face actions
        for user in users:
            user["_id"] = str(user["_id"])
            user["face_registered"] = is_face_registered(user["_id"])
            user["role_name"] = "Employee"

            # Button: Register OR View/Update Face
            if user["face_registered"]:
                user["face_action"] = {
                    "label": "View / Update Face",
                    "url": url_for("employee_users.update_face", user_id=user["_id"]),
                    "class": "btn btn-success btn-sm"
                }
            else:
                user["face_action"] = {
                    "label": "Register Face",
                    "url": url_for("employee_users.register_face", user_id=user["_id"]),
                    "class": "btn btn-primary btn-sm"
                }

        return render_template("hr/viewEmployees.html", users=users)

    except Exception as e:
        print(f"[ERROR] {e}")
        flash(f"Error fetching employees: {e}", "danger")
        return render_template("hr/viewEmployees.html", users=[])


# -------------------------------------------------------------
# ADD EMPLOYEE
# -------------------------------------------------------------
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
                "face_data": {},
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


# -------------------------------------------------------------
# UPDATE EMPLOYEE
# -------------------------------------------------------------
@hr_employee_bp.route("/edituser/<user_id>", methods=["GET", "POST"])
@login_required
def edit_user(user_id):
    try:
        user = mongo.db.users.find_one({"_id": ObjectId(user_id)})
        if not user:
            flash("Employee not found!", "danger")
            return redirect(url_for("employee_users.view_users"))

        if request.method == "POST":
            mongo.db.users.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": {
                    "name": request.form.get("name"),
                    "email": request.form.get("email"),
                    "phone": request.form.get("phone"),
                    "department": request.form.get("department"),
                    "designation": request.form.get("designation"),
                    "status": request.form.get("status"),
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


# -------------------------------------------------------------
# DELETE EMPLOYEE
# -------------------------------------------------------------
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
# REGISTER FACE (Live View)
# -----------------------------
@hr_employee_bp.route("/register_face/<user_id>")
@login_required
def register_face(user_id):
    user = mongo.db.users.find_one({"_id": ObjectId(user_id)})
    if not user:
        flash("Employee not found!", "danger")
        return redirect(url_for("employee_users.view_users"))

    # Render live view page
    return render_template("hr/faceCapture.html", user=user, action="register")


# -----------------------------
# UPDATE FACE (View old + Live)
# -----------------------------
@hr_employee_bp.route("/update_face/<user_id>")
@login_required
def update_face(user_id):
    user = mongo.db.users.find_one({"_id": ObjectId(user_id)})
    if not user:
        flash("Employee not found!", "danger")
        return redirect(url_for("employee_users.view_users"))

    # Fetch old image preview (first face)
    old_images = []
    if user.get("face_data", {}).get("images"):
        old_images = user["face_data"]["images"]

    print(old_images)

    return render_template("hr/faceCapture.html", user=user, action="update", old_images=old_images)


# -----------------------------
# STREAM CAMERA FEED
# -----------------------------
@hr_employee_bp.route("/video_feed/<user_id>")
@login_required
def video_feed(user_id):
    """Stream live webcam feed for registration preview."""
    return Response(generate_camera_frames(), mimetype="multipart/x-mixed-replace; boundary=frame")


# -----------------------------
# ACTUAL FACE CAPTURE TRIGGER
# -----------------------------
@hr_employee_bp.route("/capture_face/<user_id>/<action>")
@login_required
def capture_face_action(user_id, action):
    """Captures faces and stores them when triggered."""
    user = mongo.db.users.find_one({"_id": ObjectId(user_id)})
    if not user:
        flash("Employee not found!", "danger")
        return redirect(url_for("employee_users.view_users"))

    folder_path = capture_faces_for_user(user_id, user["name"])
    if folder_path:
        if action == "register":
            flash("Face registered successfully!", "success")
        else:
            flash("Face updated successfully!", "success")
    else:
        flash("No faces captured. Try again.", "warning")

    return redirect(url_for("employee_users.view_users"))
