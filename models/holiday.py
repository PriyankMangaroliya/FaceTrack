from utils.db import mongo
from datetime import datetime

class Holiday:

    @staticmethod
    def collection():
        return mongo.db.holidays

    def __init__(self, institute_id, title, description=None, date=None,
                 type=None, created_at=None, updated_at=None):
        self.institute_id = institute_id
        self.title = title
        self.description = description
        self.date = date
        self.type = type  # "National", "Religious", "Custom", "Weekend"
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()

    def to_dict(self):
        return {
            "institute_id": self.institute_id,
            "title": self.title,
            "description": self.description,
            "date": self.date,
            "type": self.type,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
