from utils.db import mongo
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from bson import ObjectId

class User:

    @staticmethod
    def collection():
        return mongo.db.users

    def __init__(self, name, email, phone, password, role_id=None, institute_id=None,
                 department=None, designation=None, face_data=None, status="Active",
                 created_at=None, updated_at=None):
        self.name = name
        self.email = email
        self.phone = phone
        # Hash the password for security
        self.password = generate_password_hash(password)
        self.role_id = ObjectId(role_id) if role_id else None
        self.institute_id = ObjectId(institute_id) if institute_id else None
        self.department = department
        self.designation = designation
        self.face_data = face_data
        self.status = status
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()

    def to_dict(self):
        return {
            "name": self.name,
            "email": self.email,
            "phone": self.phone,
            "password": self.password,
            "role_id": self.role_id,
            "institute_id": self.institute_id,
            "department": self.department,
            "designation": self.designation,
            "face_data": self.face_data,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }

    # Save user to MongoDB
    def save(self):
        return self.collection().insert_one(self.to_dict())

    # Find user by email
    @staticmethod
    def find_by_email(email):
        return User.collection().find_one({"email": email})

    # Verify password for login
    @staticmethod
    def verify_password(email, password):
        user = User.find_by_email(email)
        if user and check_password_hash(user["password"], password):
            return user
        return None
