# Role Schema (MongoDB)
role_schema = {
    "_id": "ObjectId",
    "name": "String",
    "permissions": "Array",         # e.g. ["mark_attendance", "view_report"]
    "description": "String",
    "created_at": "Date"
}
