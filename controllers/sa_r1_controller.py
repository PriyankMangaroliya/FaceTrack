from flask import Blueprint, render_template, request, make_response
from bson import ObjectId
from utils.db import mongo
from utils.auth import login_required
from openpyxl import Workbook
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas
import io, csv

sa_reports_bp = Blueprint("sa_reports", __name__, url_prefix="/systemadmin/reports")


@sa_reports_bp.route("/institute", methods=["GET"])
@login_required
def institute_report():
    """
    View institute report — show HR/Admins and Employees separately.
    """
    institute_id = request.args.get("institute_id")
    export_type = request.args.get("export")

    # Fetch all institutes for dropdown
    institutes = list(mongo.db.institute.find({}, {"name": 1}))
    selected_institute = None

    if institute_id:
        try:
            selected_institute = mongo.db.institute.find_one({"_id": ObjectId(institute_id)})
        except Exception:
            selected_institute = None

    hr_list, employee_list = [], []

    if selected_institute:
        # Identify HR/Admin roles from roles collection
        roles = list(mongo.db.roles.find({}))
        hr_role_ids = [r["_id"] for r in roles if r.get("name", "").lower() in ["hr", "admin", "human resources", "hr manager"]]

        # Fetch users for selected institute
        all_users = list(mongo.db.users.find({"institute_id": ObjectId(selected_institute["_id"])}))

        for user in all_users:
            role_id = user.get("role_id")
            if role_id in hr_role_ids:
                hr_list.append(user)
            else:
                employee_list.append(user)

    # Export Options
    if export_type:
        if export_type.lower() == "csv":
            return _export_csv(selected_institute, hr_list, employee_list)
        elif export_type.lower() == "xlsx":
            return _export_excel(selected_institute, hr_list, employee_list)
        elif export_type.lower() == "pdf":
            return _export_pdf(selected_institute, hr_list, employee_list)

    # Render HTML
    return render_template(
        "systemadmin/viewReport1.html",
        institutes=institutes,
        institute=selected_institute,
        hr_list=hr_list,
        employee_list=employee_list
    )


# ===================== EXPORT HELPERS =====================

def _export_csv(institute, hr_list, employee_list):
    buffer = io.StringIO()
    writer = csv.writer(buffer)

    writer.writerow(["Institute Report"])
    writer.writerow(["Institute Name", institute.get("name", "")])
    writer.writerow(["Type", institute.get("institute_type", "")])
    writer.writerow(["Email", institute.get("email", "")])
    writer.writerow(["Address", institute.get("address", "")])
    writer.writerow([])

    writer.writerow(["HR / Admin Details"])
    writer.writerow(["#", "Name", "Email", "Phone", "Department", "Designation", "Status"])
    for i, hr in enumerate(hr_list, start=1):
        writer.writerow([
            i, hr.get("name", ""), hr.get("email", ""), hr.get("phone", ""),
            hr.get("department", ""), hr.get("designation", ""), hr.get("status", "")
        ])
    writer.writerow([])

    writer.writerow(["Employee Details"])
    writer.writerow(["#", "Name", "Email", "Phone", "Department", "Designation", "Status"])
    for i, emp in enumerate(employee_list, start=1):
        writer.writerow([
            i, emp.get("name", ""), emp.get("email", ""), emp.get("phone", ""),
            emp.get("department", ""), emp.get("designation", ""), emp.get("status", "")
        ])

    resp = make_response(buffer.getvalue())
    resp.headers["Content-Disposition"] = f"attachment; filename=institute_report_{institute['_id']}.csv"
    resp.headers["Content-Type"] = "text/csv; charset=utf-8"
    return resp


def _export_excel(institute, hr_list, employee_list):
    wb = Workbook()
    ws = wb.active
    ws.title = "Institute Report"

    ws.append(["Institute Report"])
    ws.append(["Name", institute.get("name", "")])
    ws.append(["Type", institute.get("institute_type", "")])
    ws.append(["Email", institute.get("email", "")])
    ws.append(["Address", institute.get("address", "")])
    ws.append([])

    ws.append(["HR / Admin Details"])
    ws.append(["#", "Name", "Email", "Phone", "Department", "Designation", "Status"])
    for i, hr in enumerate(hr_list, start=1):
        ws.append([
            i, hr.get("name", ""), hr.get("email", ""), hr.get("phone", ""),
            hr.get("department", ""), hr.get("designation", ""), hr.get("status", "")
        ])
    ws.append([])

    ws.append(["Employee Details"])
    ws.append(["#", "Name", "Email", "Phone", "Department", "Designation", "Status"])
    for i, emp in enumerate(employee_list, start=1):
        ws.append([
            i, emp.get("name", ""), emp.get("email", ""), emp.get("phone", ""),
            emp.get("department", ""), emp.get("designation", ""), emp.get("status", "")
        ])

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    resp = make_response(buffer.getvalue())
    resp.headers["Content-Disposition"] = f"attachment; filename=institute_report_{institute['_id']}.xlsx"
    resp.headers["Content-Type"] = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    return resp


def _export_pdf(institute, hr_list, employee_list):
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 80

    p.setFont("Helvetica-Bold", 16)
    p.drawString(2 * cm, y, f"Institute Report - {institute.get('name', '')}")
    y -= 25

    p.setFont("Helvetica", 11)
    p.drawString(2 * cm, y, f"Type: {institute.get('institute_type', '')}")
    y -= 15
    p.drawString(2 * cm, y, f"Email: {institute.get('email', '')}")
    y -= 15
    p.drawString(2 * cm, y, f"Address: {institute.get('address', '')}")
    y -= 25

    # HR Section
    p.setFont("Helvetica-Bold", 13)
    p.drawString(2 * cm, y, "HR / Admin Details:")
    y -= 15
    p.setFont("Helvetica", 10)
    for i, hr in enumerate(hr_list, start=1):
        line = f"{i}. {hr.get('name', '')} | {hr.get('email', '')} | {hr.get('designation', '')}"
        p.drawString(2 * cm, y, line)
        y -= 12
        if y < 100:
            p.showPage()
            y = height - 80

    y -= 20
    p.setFont("Helvetica-Bold", 13)
    p.drawString(2 * cm, y, "Employee Details:")
    y -= 15
    p.setFont("Helvetica", 10)
    for i, emp in enumerate(employee_list, start=1):
        line = f"{i}. {emp.get('name', '')} | {emp.get('email', '')} | {emp.get('designation', '')}"
        p.drawString(2 * cm, y, line)
        y -= 12
        if y < 100:
            p.showPage()
            y = height - 80

    p.save()
    pdf = buffer.getvalue()
    buffer.close()

    resp = make_response(pdf)
    resp.headers["Content-Disposition"] = f"attachment; filename=institute_report_{institute['_id']}.pdf"
    resp.headers["Content-Type"] = "application/pdf"
    return resp
