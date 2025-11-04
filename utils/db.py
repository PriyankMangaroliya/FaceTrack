"""
utils/db.py
-----------------
This module initializes and manages the MongoDB connection
for the entire Flask application.
"""

from flask_pymongo import PyMongo

# Create a global MongoDB instance
mongo = PyMongo()

def init_db_connection(app):
    """
    Initialize MongoDB connection with Flask app.
    Loads settings from config.py (like MONGO_URI).
    """
    from config import Config
    app.config.from_object(Config)
    mongo.init_app(app)

    print("MongoDB connection initialized successfully.")
    return mongo
