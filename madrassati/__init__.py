from flask import Flask
from madrassati.blueprints.auth import auth_bp
from madrassati.extensions import db ,migrate   ,flask_limiter
from madrassati.errors import handle_404, handle_401, handle_500
app = Flask(__name__)
app.config.from_object("madrassati.config.Config")
db.init_app(app)
migrate.init_app(app, db)
flask_limiter.init_app(app)
#register the error handlers
app.register_error_handler(404, handle_404)
app.register_error_handler(401, handle_401)
app.register_error_handler(500, handle_500)
#register the blueprint for authentification
app.register_blueprint(auth_bp)
import madrassati.views
