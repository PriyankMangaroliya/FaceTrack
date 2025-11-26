from flask import Blueprint, render_template, session
from utils.auth import login_required
from utils.db import mongo
from bson import ObjectId
from datetime import datetime

employee_bp = Blueprint("employee", __name__, url_prefix="/employee")


@employee_bp.route("/dashboard")
@login_required
def dashboard():
    user_id = session.get("user_id")

    # ------ Fetch Logged-in User ------
    user = mongo.db.users.find_one({"_id": ObjectId(user_id)})
    if not user:
        return "User not found", 404

    # ------ Fetch Attendance Records ------
    attendance_records = list(
        mongo.db.attendances.find({"user_id": str(user_id)})
            .sort("date", -1)
    )

    # ------ Summary Counts ------
    summary = {
        "present": mongo.db.attendances.count_documents({"user_id": str(user_id), "status": "present"}),
        "late": mongo.db.attendances.count_documents({"user_id": str(user_id), "status": "late"}),
        "dayoff": mongo.db.attendances.count_documents({"user_id": str(user_id), "status": "dayoff"}),
        "overtime": mongo.db.attendances.count_documents({"user_id": str(user_id), "status": "overtime"}),
    }

    # ------ Monthly Graph (Last 30 Days) ------
    pipeline = [
        {
            "$match": {"user_id": str(user_id)}
        },
        {
            "$project": {
                "date": 1,
                "status": 1,
                "dateObj": {"$dateFromString": {"dateString": "$date"}}
            }
        },
        {
            "$group": {
                "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$dateObj"}},
                "present": {"$sum": {"$cond": [{"$eq": ["$status", "present"]}, 1, 0]}},
                "late": {"$sum": {"$cond": [{"$eq": ["$status", "late"]}, 1, 0]}},
                "dayoff": {"$sum": {"$cond": [{"$eq": ["$status", "dayoff"]}, 1, 0]}},
                "overtime": {"$sum": {"$cond": [{"$eq": ["$status", "overtime"]}, 1, 0]}},
            }
        },
        {"$sort": {"_id": 1}}
    ]

    monthly_data = list(mongo.db.attendances.aggregate(pipeline))

    labels = [d["_id"] for d in monthly_data]
    present_data = [d["present"] for d in monthly_data]
    late_data = [d["late"] for d in monthly_data]
    dayoff_data = [d["dayoff"] for d in monthly_data]
    overtime_data = [d["overtime"] for d in monthly_data]

    return render_template(
        "employee/index.html",
        user=user,
        records=attendance_records,
        summary=summary,
        labels=labels,
        present_data=present_data,
        late_data=late_data,
        dayoff_data=dayoff_data,
        overtime_data=overtime_data
    )
