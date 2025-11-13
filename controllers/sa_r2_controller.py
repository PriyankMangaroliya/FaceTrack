from flask import Blueprint, render_template, request, make_response
from bson import ObjectId
from utils.db import mongo
from utils.auth import login_required
from openpyxl import Workbook
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
import io, csv

sa_attendance_bp = Blueprint("sa_attendance", __name__, url_prefix="/systemadmin/reports")


@sa_attendance_bp.route("/attendance", methods=["GET"])
@login_required
def institute_attendance_report():
    """System Admin: View institute-wise attendance (single combined table)."""
    institute_id = request.args.get("institute_id")
    export_type = request.args.get("export")

    # Fetch all institutes for dropdown
    institutes = list(mongo.db.institute.find({}, {"name": 1}))

    # If no institute is selected yet
    if not institute_id:
        return render_template(
            "systemadmin/viewReport2.html",
            institutes=institutes,
            institute=None,
            attendance_list=[]
        )

    # Fetch selected institute
    try:
        institute = mongo.db.institute.find_one({"_id": ObjectId(institute_id)})
    except Exception:
        # fallback if invalid ObjectId or stored differently
        institute = mongo.db.institute.find_one({"_id": institute_id})

    if not institute:
        return render_template(
            "systemadmin/viewReport2.html",
            institutes=institutes,
            institute=None,
            attendance_list=[]
        )

    # ----------------------------
    # Fetch users of this institute
    # ----------------------------
    users = list(mongo.db.users.find({
        "$or": [
            {"institute_id": ObjectId(institute_id)},
            {"institute_id": institute_id}
        ]
    }))

    user_map = {str(u["_id"]): u for u in users}
    user_ids_obj = [u["_id"] for u in users]
    user_ids_str = [str(u["_id"]) for u in users]

    # ----------------------------
    # Fetch attendance (handle both ObjectId & string user_id)
    # ----------------------------
    attendance_cursor = mongo.db.attendances.find({
        "$or": [
            {"user_id": {"$in": user_ids_obj}},
            {"user_id": {"$in": user_ids_str}}
        ]
    })

    attendance_list = []
    for rec in attendance_cursor:
        user = user_map.get(str(rec.get("user_id")))
        if not user:
            continue
        attendance_list.append({
            "name": user.get("name", ""),
            "email": user.get("email", ""),
            "designation": user.get("designation", ""),
            "date": rec.get("date", ""),
            "status": rec.get("status", "Present"),
            "remarks": rec.get("remarks", ""),
        })

    # ----------------------------
    # EXPORT OPTIONS
    # ----------------------------
    if export_type:
        export_type = export_type.lower()
        if export_type == "csv":
            return _export_csv(institute, attendance_list)
        elif export_type == "xlsx":
            return _export_excel(institute, attendance_list)
        elif export_type == "pdf":
            return _export_pdf(institute, attendance_list)

    # ----------------------------
    # RENDER HTML TEMPLATE
    # ----------------------------
    return render_template(
        "systemadmin/viewReport2.html",
        institutes=institutes,
        institute=institute,
        attendance_list=attendance_list
    )


# ================= EXPORT HELPERS =================

def _export_csv(institute, records):
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["Institute Attendance Report"])
    writer.writerow(["Institute:", institute.get("name", "")])
    writer.writerow([])
    writer.writerow(["#", "Name", "Email", "Designation", "Date", "Status", "Remarks"])
    for i, row in enumerate(records, start=1):
        writer.writerow([i, row["name"], row["email"], row["designation"], row["date"], row["status"], row["remarks"]])
    resp = make_response(buffer.getvalue())
    resp.headers["Content-Disposition"] = f"attachment; filename=attendance_{institute['_id']}.csv"
    resp.headers["Content-Type"] = "text/csv"
    return resp


def _export_excel(institute, records):
    wb = Workbook()
    ws = wb.active
    ws.title = "Attendance Report"
    ws.append(["Institute:", institute.get("name", "")])
    ws.append([])
    ws.append(["#", "Name", "Email", "Designation", "Date", "Status", "Remarks"])
    for i, row in enumerate(records, start=1):
        ws.append([i, row["name"], row["email"], row["designation"], row["date"], row["status"], row["remarks"]])
    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    resp = make_response(buffer.getvalue())
    resp.headers["Content-Disposition"] = f"attachment; filename=attendance_{institute['_id']}.xlsx"
    resp.headers["Content-Type"] = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    return resp


def _export_pdf(institute, records):
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 80
    p.setFont("Helvetica-Bold", 14)
    p.drawString(60, y, f"Attendance Report - {institute.get('name', '')}")
    y -= 30
    p.setFont("Helvetica", 10)
    for i, row in enumerate(records, start=1):
        line = f"{i}. {row['name']} | {row['designation']} | {row['date']} | {row['status']} | {row['remarks']}"
        p.drawString(60, y, line)
        y -= 12
        if y < 100:
            p.showPage()
            y = height - 80
    p.save()
    pdf = buffer.getvalue()
    buffer.close()
    resp = make_response(pdf)
    resp.headers["Content-Disposition"] = f"attachment; filename=attendance_{institute['_id']}.pdf"
    resp.headers["Content-Type"] = "application/pdf"
    return resp
