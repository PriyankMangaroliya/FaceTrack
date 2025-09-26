from flask import Flask, render_template
from utils.db import init_db_connection, users_col

app = Flask(__name__)

# Initialize MongoDB from config.py
init_db_connection(app)

@app.route('/')
def home():
    users = list(users_col().find({}, {"_id": 0}))
    return {"users_count": len(users)}

@app.route("/login")
def login():
    return render_template("auth-login.html")

@app.route("/register")
def register():
    return render_template("auth-register.html")

if __name__ == '__main__':
    app.run(debug=True)