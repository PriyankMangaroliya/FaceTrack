from flask import Blueprint, render_template, session
from utils.auth import login_required
from utils.db import mongo
from datetime import datetime, timedelta
from bson import ObjectId

hr_bp = Blueprint("hr", __name__, url_prefix="/hr")


@hr_bp.route("/index")
@login_required
def index():
    # -------------------------------------------------
    # 1. LOGGED-IN USER
    # -------------------------------------------------
    user_id = session.get("user_id")
    if not user_id:
        return "User not logged in", 401

    logged_user = mongo.db.users.find_one({"_id": ObjectId(user_id)})
    if not logged_user:
        return "User not found", 404

    institute_id = logged_user.get("institute_id")
    if not institute_id:
        return "Institute not found for this user", 404

    inst_str = str(institute_id)
    today = datetime.now().strftime("%Y-%m-%d")

    # -------------------------------------------------
    # 2. REQUIRED ROLES  (HR + Employee)
    # -------------------------------------------------
    hr_role = mongo.db.roles.find_one({"name": "HR"})
    hr_role_id = hr_role["_id"] if hr_role else None

    emp_role = mongo.db.roles.find_one({"name": "Employee"})
    emp_role_id = emp_role["_id"] if emp_role else None

    # -------------------------------------------------
    # 3. REQUIRED COUNTS (HR + Employee)
    # -------------------------------------------------
    total_hr = mongo.db.users.count_documents({
        "role_id": hr_role_id,
        "institute_id": institute_id
    })

    active_hr = mongo.db.users.count_documents({
        "role_id": hr_role_id,
        "institute_id": institute_id,
        "status": "Active"
    })

    total_employee = mongo.db.users.count_documents({
        "role_id": emp_role_id,
        "institute_id": institute_id
    })

    active_employee = mongo.db.users.count_documents({
        "role_id": emp_role_id,
        "institute_id": institute_id,
        "status": "Active"
    })

    # -------------------------------------------------
    # 4. REQUIRED — TODAY PRESENT / ABSENT
    # -------------------------------------------------
    today_present = mongo.db.attendances.count_documents({
        "institute_id": inst_str,
        "date": today
    })

    today_absent = total_employee - today_present

    # -------------------------------------------------
    # 5. REQUIRED — HOLIDAYS THIS MONTH
    # -------------------------------------------------
    current_month = datetime.now().month

    total_holiday_month = mongo.db.holidays.count_documents({
        "institute_id": institute_id,
        "$expr": {"$eq": [{"$month": "$date"}, current_month]}
    })

    # -------------------------------------------------
    # 6. WEEKLY (LAST 7 DAYS) — REQUIRED
    # -------------------------------------------------
    labels = []
    present_data = []
    absent_data = []

    for i in range(7):
        day = datetime.now() - timedelta(days=i)
        day_str = day.strftime("%Y-%m-%d")

        labels.append(day.strftime("%d %b"))

        present = mongo.db.attendances.count_documents({
            "institute_id": inst_str,
            "date": day_str
        })
        absent = total_employee - present

        present_data.append(present)
        absent_data.append(absent)

    labels.reverse()
    present_data.reverse()
    absent_data.reverse()

    # -------------------------------------------------
    # 7. MONTHLY 30 DAYS — REQUIRED
    # -------------------------------------------------
    month_labels = []
    month_present_data = []
    month_absent_data = []

    for i in range(30):
        day = datetime.now() - timedelta(days=i)
        day_str = day.strftime("%Y-%m-%d")

        month_labels.append(day.strftime("%d %b"))

        present = mongo.db.attendances.count_documents({
            "institute_id": inst_str,
            "date": day_str
        })
        absent = total_employee - present

        month_present_data.append(present)
        month_absent_data.append(absent)

    month_labels.reverse()
    month_present_data.reverse()
    month_absent_data.reverse()

    # -------------------------------------------------
    # RENDER HTML WITH ALL REQUIRED DATA
    # -------------------------------------------------
    return render_template(
        "hr/index.html",
        total_hr=total_hr,
        active_hr=active_hr,
        total_employee=total_employee,
        active_employee=active_employee,
        today_present=today_present,
        today_absent=today_absent,
        total_holiday_month=total_holiday_month,

        # weekly chart data
        labels=labels,
        present_data=present_data,
        absent_data=absent_data,

        # monthly chart data
        month_labels=month_labels,
        month_present_data=month_present_data,
        month_absent_data=month_absent_data
    )
