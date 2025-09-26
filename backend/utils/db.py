from flask_pymongo import PyMongo

# Create PyMongo object
mongo = PyMongo()

def init_db_connection(app):
    app.config["MONGO_URI"] = "mongodb://localhost:27017/AttendanceSystem"
    mongo.init_app(app)

# ✅ Collections (shortcuts)
users_col = lambda: mongo.db.users
attendance_col = lambda: mongo.db.attendances
roles_col = lambda: mongo.db.roles
organizations_col = lambda: mongo.db.organizations
attendance_settings_col = lambda: mongo.db.attendance_settings
