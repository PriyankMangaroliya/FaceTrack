from flask import Blueprint, render_template, request, send_file, flash, session
from utils.auth import login_required
from bson import ObjectId
from datetime import datetime
import io, csv
from openpyxl import Workbook
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from models.users import User
from models.attendance import Attendance
from calendar import monthrange, month_name
from datetime import datetime, timedelta

hr_report_bp = Blueprint("hr_report", __name__, url_prefix="/hr/reports")


@hr_report_bp.route("/attendance", methods=["GET", "POST"])
@login_required
def view_report():
    hr_user_id = session.get("user_id")
    if not hr_user_id:
        flash("Session expired. Please login again.", "danger")
        return render_template("hr/viewReport1.html", employees=[], report_data=None)

    hr_user = User.find_by_id(hr_user_id)
    if not hr_user:
        flash("HR user not found.", "danger")
        return render_template("hr/viewReport1.html", employees=[], report_data=None)

    institute_id = hr_user.get("institute_id")
    if not institute_id:
        flash("HR does not belong to any institute.", "danger")
        return render_template("hr/viewReport1.html", employees=[], report_data=None)

    employees = list(User.collection().find({"institute_id": ObjectId(institute_id)}))

    report_data = []
    selected_employee = None
    selected_month = None
    month_days = []

    if request.method == "POST":
        selected_employee = request.form.get("employee_id")
        selected_month = request.form.get("month")  # format YYYY-MM
        if selected_employee and selected_month:
            year, month = map(int, selected_month.split('-'))
            num_days = monthrange(year, month)[1]  # total days in month
            # Generate list of dates
            month_days = [datetime(year, month, day) for day in range(1, num_days + 1)]

            start_date = month_days[0]
            end_date = month_days[-1] + timedelta(days=1)

            # Fetch all attendance for employee in month
            attendance_records = list(Attendance.collection().find({
                "user_id": ObjectId(selected_employee),
                "date": {"$gte": start_date, "$lt": end_date}
            }).sort("date", 1))

            # Convert to dict keyed by date for easy lookup
            attendance_dict = {rec['date'].date(): rec for rec in attendance_records}

            # Prepare report_data for template: each day of month
            report_data = []
            for day in month_days:
                rec = attendance_dict.get(day.date())
                if rec:
                    report_data.append(rec)
                else:
                    report_data.append({
                        "date": day,
                        "entries": []
                    })
        else:
            flash("Please select both employee and month.", "danger")

    return render_template("hr/viewReport1.html",
                           employees=employees,
                           report_data=report_data,
                           selected_employee=selected_employee,
                           selected_month=selected_month)


# ---------------- Export CSV ----------------
@hr_report_bp.route("/export/csv/<employee_id>/<month>")
@login_required
def export_csv(employee_id, month):
    year, month_num = map(int, month.split('-'))
    start_date = datetime(year, month_num, 1)
    if month_num == 12:
        end_date = datetime(year + 1, 1, 1)
    else:
        end_date = datetime(year, month_num + 1, 1)

    data = list(Attendance.collection().find({
        "user_id": ObjectId(employee_id),
        "date": {"$gte": start_date, "$lt": end_date}
    }).sort("date", 1))

    si = io.StringIO()
    cw = csv.writer(si)
    cw.writerow(["Date", "Time In", "Time Out", "Duration", "Label"])
    for record in data:
        for entry in record.get("entries", []):
            cw.writerow([
                record['date'].strftime("%Y-%m-%d"),
                entry.get("in"),
                entry.get("out"),
                entry.get("duration"),
                entry.get("label")
            ])

    output = io.BytesIO()
    output.write(si.getvalue().encode('utf-8'))
    output.seek(0)
    return send_file(output, mimetype="text/csv", as_attachment=True, download_name="attendance.csv")


# ---------------- Export Excel ----------------
@hr_report_bp.route("/export/excel/<employee_id>/<month>")
@login_required
def export_excel(employee_id, month):
    year, month_num = map(int, month.split('-'))
    start_date = datetime(year, month_num, 1)
    if month_num == 12:
        end_date = datetime(year + 1, 1, 1)
    else:
        end_date = datetime(year, month_num + 1, 1)

    data = list(Attendance.collection().find({
        "user_id": ObjectId(employee_id),
        "date": {"$gte": start_date, "$lt": end_date}
    }).sort("date", 1))

    wb = Workbook()
    ws = wb.active
    ws.append(["Date", "Time In", "Time Out", "Duration", "Label"])
    for record in data:
        for entry in record.get("entries", []):
            ws.append([
                record['date'].strftime("%Y-%m-%d"),
                entry.get("in"),
                entry.get("out"),
                entry.get("duration"),
                entry.get("label")
            ])

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return send_file(output, mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                     as_attachment=True, download_name="attendance.xlsx")


# ---------------- Export PDF ----------------
@hr_report_bp.route("/export/pdf/<employee_id>/<month>")
@login_required
def export_pdf(employee_id, month):
    year, month_num = map(int, month.split('-'))
    start_date = datetime(year, month_num, 1)
    if month_num == 12:
        end_date = datetime(year + 1, 1, 1)
    else:
        end_date = datetime(year, month_num + 1, 1)

    data = list(Attendance.collection().find({
        "user_id": ObjectId(employee_id),
        "date": {"$gte": start_date, "$lt": end_date}
    }).sort("date", 1))

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 50
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, y, "Attendance Report")
    y -= 30
    c.setFont("Helvetica", 12)
    c.drawString(50, y, f"Employee ID: {employee_id}")
    c.drawString(300, y, f"Month: {month}")
    y -= 30
    c.drawString(50, y, "Date")
    c.drawString(150, y, "Time In")
    c.drawString(250, y, "Time Out")
    c.drawString(350, y, "Duration")
    c.drawString(450, y, "Label")
    y -= 20

    for record in data:
        for entry in record.get("entries", []):
            if y < 50:
                c.showPage()
                y = height - 50
            c.drawString(50, y, record['date'].strftime("%Y-%m-%d"))
            c.drawString(150, y, entry.get("in", ""))
            c.drawString(250, y, entry.get("out", ""))
            c.drawString(350, y, entry.get("duration", ""))
            c.drawString(450, y, entry.get("label", ""))
            y -= 20

    c.save()
    buffer.seek(0)
    return send_file(buffer, mimetype="application/pdf", as_attachment=True, download_name="attendance.pdf")
