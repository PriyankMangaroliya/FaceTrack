# User Schema (MongoDB)
user_schema = {
    "_id": "ObjectId",
    "name": "String",
    "email": "String",
    "phone": "String",
    "password": "String",           # hashed
    "role_id": "ObjectId",          # reference to roles
    "organization_id": "ObjectId",  # reference to organizations
    "department": "String",
    "designation": "String",
    "face_data": "Array",
    "created_at": "Date",
    "updated_at": "Date"
}
