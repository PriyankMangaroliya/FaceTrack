from flask import Flask
from config import Config
from utils.db import init_db_connection, mongo
from flask import render_template

# Import all models
from models import Role, User, Attendance, Holiday, Log, Institute

# Import controllers
from controllers.auth_controller import auth_bp
from controllers.systemadmin_controller import systemadmin_bp


# Initialize Flask app
app = Flask(__name__)
# Load configuration from Config class
app.config.from_object(Config)
# Initialize MongoDB connection
init_db_connection(app)

# Register Blueprint
app.register_blueprint(auth_bp)
app.register_blueprint(systemadmin_bp)



# Run the app
if __name__ == "__main__":
    app.run(debug=True)

