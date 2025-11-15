from flask import Flask, redirect, url_for
from config import Config
from utils.db import init_db_connection
from flask import session

# Import controllers
from controllers.auth_controller import auth_bp

from controllers.sa_controller import systemadmin_bp
from controllers.sa_roles_controller import roles_bp
from controllers.sa_institutes_controller import institutes_bp
from controllers.sa_users_controller import users_bp
from controllers.sa_r1_controller import sa_reports_bp
from controllers.sa_r2_controller import sa_attendance_bp

from controllers.hr_controller import hr_bp
from controllers.hr_users_controller import hr_users_bp
from controllers.hr_employee_controller import hr_employee_bp
from controllers.hr_attendance_controller import hr_attendance_bp
from controllers.hr_r1_controller import hr_report_bp

from controllers.emp_controller import employee_bp

app = Flask(__name__)               # Initialize Flask app
app.config.from_object(Config)      # Load configuration from Config class
init_db_connection(app)             # Initialize MongoDB connection

# Register Blueprint
app.register_blueprint(auth_bp)

app.register_blueprint(systemadmin_bp)
app.register_blueprint(roles_bp)
app.register_blueprint(institutes_bp)
app.register_blueprint(users_bp)
app.register_blueprint(sa_reports_bp)
app.register_blueprint(sa_attendance_bp)

app.register_blueprint(hr_bp)
app.register_blueprint(hr_users_bp)
app.register_blueprint(hr_employee_bp)
app.register_blueprint(hr_attendance_bp)
app.register_blueprint(hr_report_bp)

app.register_blueprint(employee_bp)




# It globally injects user_name from the session into all Flask templates
# so you can directly use {{ user_name }} anywhere without passing it manually.
@app.context_processor
def inject_user():
    return dict(user_name=session.get("user_name"))


# Global before_request: block all routes except login/logout if not logged in
@app.before_request
def require_login():
    from flask import request
    allowed_routes = ["auth.login", "auth.logout", "static"]

    # if not logged in and route not in allowed list
    if "user_id" not in session and request.endpoint not in allowed_routes:
        return redirect(url_for("auth.login"))
    return None


# Run the app
if __name__ == "__main__":
    app.run(debug=True)