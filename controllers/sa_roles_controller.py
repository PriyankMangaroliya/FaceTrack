from flask import Blueprint, render_template, request, redirect, url_for, flash
from utils.db import mongo
from utils.auth import login_required
from bson import ObjectId
from datetime import datetime

roles_bp = Blueprint("roles", __name__, url_prefix="/systemadmin/roles")

# View Roles
@roles_bp.route("/viewroles")
@login_required
def view_roles():
    try:
        roles = list(mongo.db.roles.find())
        for role in roles:
            role["_id"] = str(role["_id"])
        return render_template("systemadmin/viewRole.html", roles=roles)
    except Exception as e:
        flash(f"Error fetching roles: {e}", "danger")
        return render_template("systemadmin/viewRole.html", roles=[])


# Add Role
@roles_bp.route("/addrole", methods=["GET", "POST"])
@login_required
def add_role():
    if request.method == "POST":
        name = request.form.get("name")
        description = request.form.get("description")

        if not name:
            flash("Role name is required.", "warning")
            return redirect(url_for("roles.add_role"))

        mongo.db.roles.insert_one({
            "name": name,
            "description": description,
            "created_at": datetime.utcnow()
        })
        flash("Role added successfully!", "success")
        return redirect(url_for("roles.view_roles"))

    return render_template("systemadmin/manageRole.html", role=None)


# Edit / Update Existing Role
@roles_bp.route("/editrole/<role_id>", methods=["GET", "POST"])
@login_required
def edit_role(role_id):
    role = mongo.db.roles.find_one({"_id": ObjectId(role_id)})

    if not role:
        flash("Role not found!", "danger")
        return redirect(url_for("roles.view_roles"))

    if request.method == "POST":
        name = request.form.get("name")
        description = request.form.get("description")

        mongo.db.roles.update_one(
            {"_id": ObjectId(role_id)},
            {"$set": {
                "name": name,
                "description": description,
                "updated_at": datetime.utcnow()
            }}
        )

        flash("Role updated successfully!", "success")
        return redirect(url_for("roles.view_roles"))

    return render_template("systemadmin/manageRole.html", role=role)


# Delete Roles
@roles_bp.route("/deleterole/<role_id>")
@login_required
def delete_role(role_id):
    try:
        role = mongo.db.roles.find_one({"_id": ObjectId(role_id)})

        if not role:
            flash("Role not found!", "danger")
            return redirect(url_for("roles.view_roles"))

        if role["name"] == "System Admin":
            flash("System Admin role cannot be deleted!", "warning")
            return redirect(url_for("roles.view_roles"))

        mongo.db.roles.delete_one({"_id": ObjectId(role_id)})
        flash("Role deleted successfully!", "success")

    except Exception as e:
        flash(f"Error deleting role: {e}", "danger")

    return redirect(url_for("roles.view_roles"))
