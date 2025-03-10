from flask import Flask
from madrassati.blueprints.auth import auth_bp
from madrassati.extensions import db ,migrate
app = Flask(__name__)
app.config.from_object("madrassati.config.Config")
db.init_app(app)
migrate.init_app(app, db)
#register the blueprint for authentification
app.register_blueprint(auth_bp)
import madrassati.views
