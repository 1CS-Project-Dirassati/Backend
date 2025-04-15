from flask import Flask, request, Response
from flask_restx import Api
from madrassati.extensions import db, migrate, flask_limiter, cors, redis_client

# import the namespace from auth
from .blueprints.api.auth import auth_ns
from .blueprints.api.protected.admin import admin_ns

api = Api(
    title="Madrassati API",
    version="1.0",
    description="madrassati API",
)
USERNAME = "pipi"
PASSWORD = "pipitipop69"


def check_auth():
    auth = request.authorization
    return auth and auth.username == USERNAME and auth.password == PASSWORD


app = Flask(__name__)


@app.before_request
def protect_docs():
    if request.path.startswith("/docs") or request.path.startswith("/swagger"):
        if not check_auth():
            return Response(
                "Could not verify your access to the documentation.\n"
                "You have to login with proper credentials",
                401,
                {"WWW-Authenticate": 'Basic realm="Login Required"'},
            )


app.config.from_object("madrassati.config.Config")
cors.init_app(app)
db.init_app(app)
redis_client.init_app(app)
migrate.init_app(app, db)
flask_limiter.init_app(app)
api.init_app(app)
api.add_namespace(auth_ns)
api.add_namespace(admin_ns)
# register the blueprint for authentification
