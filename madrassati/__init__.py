from flask import Flask
from flask_restx import Api
from madrassati.extensions import db ,migrate   ,flask_limiter , cors

#import the namespace from auth
from .blueprints.api.auth import auth_ns
api = Api(
    title='Madrassati API',
    version='1.0',
    description='madrassati API',

)
app = Flask(__name__)
app.config.from_object("madrassati.config.Config")
cors.init_app(app)
db.init_app(app)
migrate.init_app(app, db)
flask_limiter.init_app(app)
api.init_app(app)
api.add_namespace(auth_ns)
#register the blueprint for authentification
