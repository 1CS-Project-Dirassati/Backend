from flask_restx import Api
from flask import Blueprint

# Import auth namespace
from .controller import api as auth_ns

authorizations = {"Bearer": {"type": "apiKey", "in": "header", "name": "Authorization"}}
auth_bp = Blueprint("auth", __name__)

auth = Api(
    auth_bp,
    title="Dirassati",
    description="Authenticate and receive tokens.",
    authorizations=authorizations,
)

# API namespaces
auth.add_namespace(auth_ns)
