from flask_pymongo import PyMongo

mongo = PyMongo()

def init_db_connection(app):
    from config import Config
    app.config.from_object(Config)
    mongo.init_app(app)
    return mongo
