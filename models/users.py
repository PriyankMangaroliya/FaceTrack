from utils.db import mongo
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from bson import ObjectId

class User:

    @staticmethod
    def collection():
        return mongo.db.users

    def __init__(self, name, email, phone, password, role_id=None, institute_id=None,
                 department=None, designation=None, face_data=None, face_registered=False,
                 status="Active", created_at=None, updated_at=None):
        self.name = name
        self.email = email
        self.phone = phone
        self.password = generate_password_hash(password)
        self.role_id = ObjectId(role_id) if role_id else None
        self.institute_id = ObjectId(institute_id) if institute_id else None
        self.department = department
        self.designation = designation

        # Face data details (path, encoding info, etc.)
        self.face_data = face_data or {}
        self.face_registered = face_registered

        self.status = status
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()

    # Convert to dictionary for MongoDB
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
            "face_registered": self.face_registered,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }

    # Save new user
    def save(self):
        return self.collection().insert_one(self.to_dict())

    # Find user by ID
    @staticmethod
    def find_by_id(user_id):
        return User.collection().find_one({"_id": ObjectId(user_id)})

    # Find user by email
    @staticmethod
    def find_by_email(email):
        return User.collection().find_one({"email": email})

    # Verify password
    @staticmethod
    def verify_password(email, password):
        user = User.find_by_email(email)
        if user and check_password_hash(user["password"], password):
            return user
        return None

    # Update face data (after registration or re-registration)
    @staticmethod
    def update_face_data(user_id, face_info):
        """
        face_info example:
        {
            "dataset_path": "dataset/John_Doe/",
            "encoding_file": "encodings.pkl",
            "last_captured": datetime.utcnow()
        }
        """
        return User.collection().update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {
                "face_data": face_info,
                "face_registered": True,
                "updated_at": datetime.utcnow()
            }}
        )

    # Check if user has face registered
    @staticmethod
    def has_face_data(user):
        return bool(user.get("face_registered"))
