# Organization Schema (MongoDB)
organization_schema = {
    "_id": "ObjectId",
    "name": "String",
    "type": "String",               # "Private" | "Public"
    "contact_number": "String",
    "address": "String",
    "attendance_type": "String",    # "in_out" | "present"
    "created_at": "Date",
    "updated_at": "Date"
}
