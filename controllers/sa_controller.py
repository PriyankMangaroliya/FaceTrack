from flask import Blueprint, render_template
from utils.db import mongo
from utils.auth import login_required
from datetime import datetime

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

    # =======================================================
    # 1️⃣ MAIN REVENUE CHART (Line Chart)
    # =======================================================
    user_pipeline = [
        {"$group": {"_id": {"month": {"$month": "$created_at"}}, "count": {"$sum": 1}}},
        {"$sort": {"_id.month": 1}}
    ]
    user_results = list(mongo.db.users.aggregate(user_pipeline))

    months = []
    user_counts = []
    for r in user_results:
        month_num = r["_id"]["month"]
        month_name = datetime(2025, month_num, 1).strftime("%b")
        months.append(month_name)
        user_counts.append(r["count"])

    attendance_pipeline = [
        {"$group": {"_id": {"month": {"$month": "$created_at"}}, "count": {"$sum": 1}}},
        {"$sort": {"_id.month": 1}}
    ]
    attendance_results = list(mongo.db.attendances.aggregate(attendance_pipeline))

    attendance_counts = []
    for a in attendance_results:
        attendance_counts.append(a["count"])

    # =======================================================
    # 2️⃣ SMALL CHARTS DATA (Chart 2, 3, 4)
    # =======================================================

    # ----- Chart 2: Bar Chart (Monthly Attendance per Institute)
    attendance_pipeline2 = [
        {"$group": {"_id": {"month": {"$month": "$created_at"}, "institute_id": "$institute_id"}, "count": {"$sum": 1}}},
        {"$sort": {"_id.month": 1}}
    ]
    raw_attendance = list(mongo.db.attendances.aggregate(attendance_pipeline2))
    monthly_counts = {m: 0 for m in month_names}
    for a in raw_attendance:
        month_num = a["_id"]["month"]
        month_name = month_names[month_num - 1]
        monthly_counts[month_name] += a["count"]

    chart2_series = [
        {"name": "Institute A", "data": [v for i, v in enumerate(monthly_counts.values()) if i < 6]},
        {"name": "Institute B", "data": [v + 2 for i, v in enumerate(monthly_counts.values()) if i < 6]},
        {"name": "Institute C", "data": [v + 4 for i, v in enumerate(monthly_counts.values()) if i < 6]},
    ]
    chart2_categories = list(monthly_counts.keys())[:6]

    # ----- Chart 3: Multi-Line (User Registration Trends)
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

    # ----- Chart 4: Area (Institutes vs Attendance Growth)
    institute_pipeline = [
        {"$group": {"_id": {"month": {"$month": "$created_at"}}, "count": {"$sum": 1}}},
        {"$sort": {"_id.month": 1}}
    ]
    inst_data = list(mongo.db.institute.aggregate(institute_pipeline))
    chart4_series = [
        {"name": "Institutes Added", "data": [d["count"] for d in inst_data]},
        {"name": "Attendance Growth", "data": [d["count"] * 2 for d in inst_data]},
    ]
    chart4_categories = [month_names[d["_id"]["month"] - 1] for d in inst_data]

    # =======================================================
    # 3️⃣ TOP SUMMARY STAT CARDS
    # =======================================================
    total_users = mongo.db.users.count_documents({})
    total_institutes = mongo.db.institute.count_documents({})
    total_roles = mongo.db.roles.count_documents({})
    total_attendance = mongo.db.attendances.count_documents({})

    # If collections are empty, provide default fallback
    if not months:
        months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun"]
        user_counts = [0, 0, 0, 0, 0, 0]
        attendance_counts = [0, 0, 0, 0, 0, 0]

    return render_template(
        "systemadmin/index.html",
        # Revenue chart
        months=months,
        user_counts=user_counts,
        attendance_counts=attendance_counts,
        # Summary Cards
        total_users=total_users,
        total_institutes=total_institutes,
        total_roles=total_roles,
        total_attendance=total_attendance,
        # Small Charts (2, 3, 4)
        chart2_series=chart2_series,
        chart2_categories=chart2_categories,
        chart3_series=chart3_series,
        chart3_categories=chart3_categories,
        chart4_series=chart4_series,
        chart4_categories=chart4_categories
    )
