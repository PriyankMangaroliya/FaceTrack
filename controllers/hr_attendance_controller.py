from flask import Blueprint, render_template, session
from datetime import datetime
from bson import ObjectId
from utils.db import mongo
from utils.auth import login_required

hr_attendance_bp = Blueprint("hr_attendance", __name__, url_prefix="/hr/attendance")


@hr_attendance_bp.route("/view")
@login_required
def view_attendance():
    user_id = str(session.get("user_id"))
    print(f"[DEBUG] HR user_id: {user_id}")
    if not user_id:
        return "User session expired or invalid.", 401

    # 🔹 Fix: Convert to ObjectId to fetch correct user
    try:
        user_doc = mongo.db.users.find_one({"_id": ObjectId(user_id)})
    except Exception:
        user_doc = mongo.db.users.find_one({"_id": user_id})

    if not user_doc:
        return "User not found in database.", 404

    institute_id = str(user_doc.get("institute_id"))
    if not institute_id:
        return "No institute assigned to this user.", 400

    today = datetime.utcnow().strftime("%Y-%m-%d")

    # Fetch all employee attendance for this institute
    records = list(
        mongo.db.attendances.find({"institute_id": institute_id, "date": today}).sort("user_id", 1)
    )

    print(f"[DEBUG] Found {len(records)} attendance records for institute {institute_id} on {today}")

    attendance_data = []
    for rec in records:
        emp_id = rec.get("user_id")
        try:
            emp_doc = mongo.db.users.find_one({"_id": ObjectId(emp_id)}) or {}
        except Exception:
            emp_doc = mongo.db.users.find_one({"_id": emp_id}) or {}

        emp_name = emp_doc.get("name", "Unknown Employee")
        entries = rec.get("entries", [])

        total_minutes = 0
        for e in entries:
            dur = e.get("duration", "").lower().replace("h", "").replace("m", "").strip()
            parts = dur.split()
            if len(parts) == 2:
                h, m = int(parts[0]), int(parts[1])
            elif len(parts) == 1:
                h, m = int(parts[0]), 0
            else:
                h, m = 0, 0
            total_minutes += (h * 60 + m)

        hours = total_minutes // 60
        mins = total_minutes % 60
        total_duration = f"{hours}h {mins}m" if total_minutes else "-"

        attendance_data.append({
            "user_name": emp_name,
            "entries": entries,
            "status": rec.get("status", "present"),
            "total_duration": total_duration
        })

    return render_template("hr/viewAttendance.html", attendance_data=attendance_data, today=today)
