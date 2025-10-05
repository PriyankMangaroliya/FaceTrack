from utils.db import mongo
from datetime import datetime

class Institute:

    @staticmethod
    def collection():
        return mongo.db.institute

    def __init__(self, name, institute_type, email=None, address=None, created_at=None, updated_at=None):
        self.name = name
        self.institute_type = institute_type  # "School", "College", "Company"
        self.email = email
        self.address = address
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()

    def to_dict(self):
        return {
            "name": self.name,
            "institute_type": self.institute_type,
            "email": self.email,
            "address": self.address,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
