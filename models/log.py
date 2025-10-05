from utils.db import mongo
from datetime import datetime

class Log:

    @staticmethod
    def collection():
        return mongo.db.logs

    def __init__(self, timestamp, action, collection_name, performed_by,
                 document_id, institute_id, changes=None):
        self.timestamp = timestamp
        self.action = action  # "INSERT", "UPDATE", "DELETE"
        self.collection_name = collection_name
        self.performed_by = performed_by
        self.document_id = document_id
        self.institute_id = institute_id
        self.changes = changes

    def to_dict(self):
        return {
            "timestamp": self.timestamp,
            "action": self.action,
            "collection": self.collection_name,
            "performed_by": self.performed_by,
            "document_id": self.document_id,
            "institute_id": self.institute_id,
            "changes": self.changes
        }
