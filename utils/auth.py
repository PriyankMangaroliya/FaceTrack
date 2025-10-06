from functools import wraps
from flask import session, redirect, url_for, flash

# This decorator makes sure that only logged-in users can access protected pages
def login_required(view_function):
    @wraps(view_function)
    def decorated_function(*args, **kwargs):
        # Check if user is logged in
        if "user_id" not in session:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for("auth.login"))  # Redirect to login page
        return view_function(*args, **kwargs)
    return decorated_function


# Optional helper function — you can call this to check login state in other routes
def is_logged_in():
    return "user_id" in session


# Optional logout helper
def logout_user():
    session.clear()
    flash("You have been logged out successfully.", "success")
    return redirect(url_for("auth.login"))
