from flask import Blueprint, render_template, request, redirect, url_for, flash
from utils.db import mongo
from utils.auth import login_required
from bson import ObjectId
from datetime import datetime

# Blueprint for institutes (nested under systemadmin)
institutes_bp = Blueprint("institutes", __name__, url_prefix="/systemadmin/institutes")


# -----------------------------
# VIEW INSTITUTES
# -----------------------------
@institutes_bp.route("/viewinstitutes")
@login_required
def view_institutes():
    try:
        institutes = list(mongo.db.institute.find())
        for i in institutes:
            i["_id"] = str(i["_id"])
        return render_template("systemadmin/viewInstitute.html", institutes=institutes)
    except Exception as e:
        flash(f"Error fetching institutes: {e}", "danger")
        return render_template("systemadmin/viewInstitute.html", institutes=[])


# -----------------------------
# ADD INSTITUTE
# -----------------------------
@institutes_bp.route("/addinstitute", methods=["GET", "POST"])
@login_required
def add_institute():
    if request.method == "POST":
        name = request.form.get("name")
        institute_type = request.form.get("institute_type")
        email = request.form.get("email")
        address = request.form.get("address")

        if not name or not institute_type:
            flash("Institute name and type are required.", "warning")
            return redirect(url_for("institutes.add_institute"))

        mongo.db.institute.insert_one({
            "name": name,
            "institute_type": institute_type,
            "email": email,
            "address": address,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        })
        flash("Institute added successfully!", "success")
        return redirect(url_for("institutes.view_institutes"))

    return render_template("systemadmin/manageInstitute.html", institute=None)


# -----------------------------
# EDIT / UPDATE INSTITUTE
# -----------------------------
@institutes_bp.route("/editinstitute/<institute_id>", methods=["GET", "POST"])
@login_required
def edit_institute(institute_id):
    institute = mongo.db.institute.find_one({"_id": ObjectId(institute_id)})

    if not institute:
        flash("Institute not found!", "danger")
        return redirect(url_for("institutes.view_institutes"))

    if request.method == "POST":
        name = request.form.get("name")
        institute_type = request.form.get("institute_type")
        email = request.form.get("email")
        address = request.form.get("address")

        mongo.db.institute.update_one(
            {"_id": ObjectId(institute_id)},
            {"$set": {
                "name": name,
                "institute_type": institute_type,
                "email": email,
                "address": address,
                "updated_at": datetime.utcnow()
            }}
        )
        flash("Institute updated successfully!", "success")
        return redirect(url_for("institutes.view_institutes"))

    institute["_id"] = str(institute["_id"])
    return render_template("systemadmin/manageInstitute.html", institute=institute)


# -----------------------------
# DELETE INSTITUTE
# -----------------------------
@institutes_bp.route("/deleteinstitute/<institute_id>")
@login_required
def delete_institute(institute_id):
    try:
        institute = mongo.db.institute.find_one({"_id": ObjectId(institute_id)})

        if not institute:
            flash("Institute not found!", "danger")
            return redirect(url_for("institutes.view_institutes"))

        mongo.db.institute.delete_one({"_id": ObjectId(institute_id)})
        flash("Institute deleted successfully!", "success")

    except Exception as e:
        flash(f"Error deleting institute: {e}", "danger")

    return redirect(url_for("institutes.view_institutes"))
