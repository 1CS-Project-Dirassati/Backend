from flask import Blueprint

# Create the blueprint
auth_bp = Blueprint("auth", __name__)

# Import views to attach routes to the blueprint
from . import views  # noqa: F401

