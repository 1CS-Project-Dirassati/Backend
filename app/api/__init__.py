from flask_restx import Api
from flask import Blueprint

from .groups.controller import api as groups_ns

# Import controller APIs as namespaces.
api_bp = Blueprint("api", __name__)
authorizations = {"Bearer": {"type": "apiKey", "in": "header", "name": "Authorization"}}


api = Api(
    api_bp,
    title="API",
    description="Main routes.",
    authorizations=authorizations,
)

# API namespaces
api.add_namespace(groups_ns)
