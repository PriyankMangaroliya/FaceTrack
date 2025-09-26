# Attendance Schema (MongoDB)
attendance_schema = {
    "_id": "ObjectId",
    "user_id": "ObjectId",          # reference to users
    "date": "Date",
    "attendance_type": "String",    # "in_out" | "present"
    "log_type": "String",           # "in" | "out"
    "session_id": "String",
    "timestamp": "Date",
    "marked_by": "String",          # "system" | "manual"
    "remarks": "String",
    "created_at": "Date",
    "updated_at": "Date"
}
