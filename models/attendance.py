from utils.db import mongo
from datetime import datetime

class Attendance:
    @staticmethod
    def collection():
        return mongo.db.attendances

    def __init__(self, user_id, institute_id, date, entries=None, status=None, remarks=None, marked_by=None,
                 correction=None, created_at=None, updated_at=None):
        self.user_id = user_id
        self.institute_id = institute_id
        self.date = date
        self.entries = entries or []
        self.status = status or "present"  # present | late | dayoff | overtime
        self.remarks = remarks
        self.marked_by = marked_by or "System"
        self.correction = correction
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()

    def to_dict(self):
        return {
            "user_id": self.user_id,
            "institute_id": self.institute_id,
            "date": self.date,
            "entries": self.entries,
            "status": self.status,
            "remarks": self.remarks,
            "marked_by": self.marked_by,
            "correction": self.correction,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    def save(self):
        Attendance.collection().insert_one(self.to_dict())


"""
entries: list of time entries in the same day.
Example:
[
    {"in": "09:00", "out": "12:30", "duration": "3:30", "label": "Morning Shift"},
    {"in": "13:30", "out": "17:00", "duration": "3:30", "label": "Afternoon Shift"},
    {"in": "18:00", "out": "20:00", "duration": "2:00", "label": "Evening Work"}
]
"""