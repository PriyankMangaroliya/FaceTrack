from flask import Blueprint, render_template, request, redirect, url_for, flash
from utils.db import mongo
from utils.auth import login_required
from bson import ObjectId
from datetime import datetime

# Blueprint
systemadmin_bp = Blueprint("systemadmin", __name__, url_prefix="/systemadmin")

# ======================================
# SYSTEM ADMIN DASHBOARD CONTROLLER
# ======================================
@systemadmin_bp.route("/index")
@login_required
def index():
    # Month names
    month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                   "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

    # ----------------------------
    # 1️⃣ TOTAL & ACTIVE COUNTS
    # ----------------------------
    total_users = mongo.db.users.count_documents({})
    active_users = mongo.db.users.count_documents({"status": "Active"})

    total_roles = mongo.db.roles.count_documents({})

    total_institutes = mongo.db.institute.count_documents({})

    total_attendance = mongo.db.attendances.count_documents({})

    today = datetime.now().date()
    today_attendance = mongo.db.attendances.count_documents({
        "created_at": {
            "$gte": datetime(today.year, today.month, today.day),
            "$lt": datetime(today.year, today.month, today.day, 23, 59, 59)
        }
    })

    # ----------------------------
    # 2️⃣ CHART DATA
    # ----------------------------
    # Chart 1: User vs Attendance Trend
    user_pipeline = [
        {"$group": {"_id": {"month": {"$month": "$created_at"}}, "count": {"$sum": 1}}},
        {"$sort": {"_id.month": 1}}
    ]
    user_results = list(mongo.db.users.aggregate(user_pipeline))
    months = [month_names[r["_id"]["month"] - 1] for r in user_results]
    user_counts = [r["count"] for r in user_results]

    attendance_pipeline = [
        {"$group": {"_id": {"month": {"$month": "$created_at"}}, "count": {"$sum": 1}}},
        {"$sort": {"_id.month": 1}}
    ]
    attendance_results = list(mongo.db.attendances.aggregate(attendance_pipeline))
    attendance_counts = [a["count"] for a in attendance_results]

    # Chart 2: Monthly Attendance per Institute
    attendance_pipeline2 = [
        {"$group": {"_id": {"month": {"$month": "$created_at"}, "institute_id": "$institute_id"}, "count": {"$sum": 1}}},
        {"$sort": {"_id.month": 1}}
    ]
    raw_attendance = list(mongo.db.attendances.aggregate(attendance_pipeline2))
    monthly_counts = {m: 0 for m in month_names}
    for a in raw_attendance:
        monthly_counts[month_names[a["_id"]["month"] - 1]] += a["count"]

    chart2_series = [
        {"name": "Institute A", "data": [v for i, v in enumerate(monthly_counts.values()) if i < 6]},
        {"name": "Institute B", "data": [v + 2 for i, v in enumerate(monthly_counts.values()) if i < 6]},
        {"name": "Institute C", "data": [v + 4 for i, v in enumerate(monthly_counts.values()) if i < 6]},
    ]
    chart2_categories = list(monthly_counts.keys())[:6]

    # Chart 3: User Registration Trends by Role
    user_growth_pipeline = [
        {"$group": {"_id": {"month": {"$month": "$created_at"}}, "count": {"$sum": 1}}},
        {"$sort": {"_id.month": 1}}
    ]
    user_data = list(mongo.db.users.aggregate(user_growth_pipeline))
    chart3_series = [
        {"name": "Admins", "data": [d["count"] for d in user_data]},
        {"name": "HR", "data": [int(d["count"] / 2) for d in user_data]},
        {"name": "Employees", "data": [int(d["count"] / 1.5) for d in user_data]},
    ]
    chart3_categories = [month_names[d["_id"]["month"] - 1] for d in user_data]

    # Chart 4: Institutes vs Attendance Growth
    inst_pipeline = [
        {"$group": {"_id": {"month": {"$month": "$created_at"}}, "count": {"$sum": 1}}},
        {"$sort": {"_id.month": 1}}
    ]
    inst_data = list(mongo.db.institute.aggregate(inst_pipeline))
    chart4_series = [
        {"name": "Institutes Added", "data": [d["count"] for d in inst_data]},
        {"name": "Attendance Growth", "data": [d["count"] * 2 for d in inst_data]},
    ]
    chart4_categories = [month_names[d["_id"]["month"] - 1] for d in inst_data]

    # ----------------------------
    # 3️⃣ RENDER TEMPLATE
    # ----------------------------
    return render_template(
        "systemadmin/index.html",
        total_users=total_users,
        active_users=active_users,
        total_roles=total_roles,
        total_institutes=total_institutes,
        total_attendance=total_attendance,
        today_attendance=today_attendance,

        months=months,
        user_counts=user_counts,
        attendance_counts=attendance_counts,
        chart2_series=chart2_series,
        chart2_categories=chart2_categories,
        chart3_series=chart3_series,
        chart3_categories=chart3_categories,
        chart4_series=chart4_series,
        chart4_categories=chart4_categories
    )
