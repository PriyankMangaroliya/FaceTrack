from utils.db import mongo
from datetime import datetime

class Attendance:

    @staticmethod
    def collection():
        return mongo.db.attendances

    def __init__(self, user_id, institute_id, date, time=None,
                 marked_by=None, status=None, remarks=None, correction=None, created_at=None, updated_at=None):
        self.user_id = user_id
        self.institute_id = institute_id
        self.date = date
        self.time = time
        self.marked_by = marked_by  # "System", "Admin", "HR"
        self.status = status
        self.remarks = remarks
        self.correction = correction
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()

    def to_dict(self):
        return {
            "user_id": self.user_id,
            "institute_id": self.institute_id,
            "date": self.date,
            "time": self.time,
            "marked_by": self.marked_by,
            "status": self.status,
            "remarks": self.remarks,
            "correction": self.correction,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
