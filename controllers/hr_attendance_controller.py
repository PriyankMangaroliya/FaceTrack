from flask import Blueprint, render_template, session, request, redirect, url_for, flash
from datetime import datetime
from bson import ObjectId
from utils.db import mongo
from utils.auth import login_required

hr_attendance_bp = Blueprint("hr_attendance", __name__, url_prefix="/hr/attendance")


# ==========================================================
# VIEW ATTENDANCE DASHBOARD
# ==========================================================
@hr_attendance_bp.route("/view")
@login_required
def view_attendance():
    user_id = str(session.get("user_id"))
    if not user_id:
        return "User session expired or invalid.", 401

    try:
        user_doc = mongo.db.users.find_one({"_id": ObjectId(user_id)})
    except Exception:
        user_doc = mongo.db.users.find_one({"_id": user_id})

    if not user_doc:
        return "User not found.", 404

    institute_id = str(user_doc.get("institute_id"))
    if not institute_id:
        return "No institute assigned to this user.", 400

    date_str = request.args.get("date", datetime.utcnow().strftime("%Y-%m-%d"))

    records = list(
        mongo.db.attendances.find({"institute_id": institute_id, "date": date_str}).sort("user_id", 1)
    )

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
            dur = e.get("duration") or ""
            if isinstance(dur, str) and ("h" in dur or "m" in dur):
                parts = dur.replace("h", "").replace("m", "").split()
                try:
                    h = int(parts[0]) if len(parts) >= 1 else 0
                    m = int(parts[1]) if len(parts) >= 2 else 0
                except ValueError:
                    h, m = 0, 0
                total_minutes += (h * 60 + m)

        hours = total_minutes // 60
        mins = total_minutes % 60
        total_duration = f"{hours}h {mins}m" if total_minutes else "-"

        attendance_data.append({
            "attendance_id": str(rec["_id"]),
            "user_id": emp_id,
            "user_name": emp_name,
            "entries": entries,
            "status": rec.get("status", "present"),
            "total_duration": total_duration
        })

    return render_template(
        "hr/viewAttendance.html",
        attendance_data=attendance_data,
        today=date_str
    )


# ==========================================================
# MANUAL ADD OUT TIME
# ==========================================================
@hr_attendance_bp.route("/add_out_time", methods=["POST"])
@login_required
def add_out_time():
    attendance_id = request.form.get("attendance_id")
    entry_index = int(request.form.get("entry_index", 0))
    out_time = request.form.get("out_time")

    if not attendance_id or not out_time:
        flash("Invalid input.", "danger")
        return redirect(url_for("hr_attendance.view_attendance"))

    record = mongo.db.attendances.find_one({"_id": ObjectId(attendance_id)})
    if not record:
        flash("Attendance record not found.", "danger")
        return redirect(url_for("hr_attendance.view_attendance"))

    entries = record.get("entries", [])
    if entry_index < len(entries):
        entry = entries[entry_index]

        # Normalize keys
        time_in = entry.get("time_in") or entry.get("in")
        entry["time_out"] = out_time

        # Calculate duration if time_in is valid
        if time_in:
            fmt = "%H:%M:%S" if len(time_in.split(":")) == 3 else "%H:%M"
            try:
                t1 = datetime.strptime(time_in, fmt)
                t2 = datetime.strptime(out_time, fmt)
                if t2 < t1:  # Next day case
                    t2 = t2.replace(day=t2.day + 1)
                diff = t2 - t1
                total_minutes = int(diff.total_seconds() // 60)
                entry["duration"] = f"{total_minutes // 60}h {total_minutes % 60}m"
            except Exception as e:
                print("[ERROR] Duration calculation failed:", e)
                entry["duration"] = "-"

        # Commit to MongoDB
        entries[entry_index] = entry
        mongo.db.attendances.update_one(
            {"_id": ObjectId(attendance_id)},
            {"$set": {"entries": entries}}
        )

        flash("✅ Out time added & duration updated successfully.", "success")
    else:
        flash("Invalid entry index.", "danger")

    return redirect(url_for("hr_attendance.view_attendance"))
