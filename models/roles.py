from utils.db import mongo
from datetime import datetime

class Role:

    @staticmethod
    def collection():
        return mongo.db.roles

    def __init__(self, name, permissions=None, description=None, created_at=None):
        self.name = name
        self.permissions = permissions or []
        self.description = description
        self.created_at = created_at or datetime.utcnow()

    def to_dict(self):
        return {
            "name": self.name,
            "permissions": self.permissions,
            "description": self.description,
            "created_at": self.created_at
        }
