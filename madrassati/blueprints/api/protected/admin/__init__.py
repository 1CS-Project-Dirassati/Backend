# protected/admin/__init__.py

from flask import Blueprint, current_app
from flask_restx import Api
import os # For static token example

# --- Admin Static Token ---
# IMPORTANT: In a real application, manage this securely (e.g., environment variables)
# This is just a simple example for a non-expiring token.
ADMIN_STATIC_TOKEN = os.environ.get("ADMIN_STATIC_TOKEN", "SUPER_SECRET_ADMIN_TOKEN_REPLACE_ME")

# --- Blueprint and API Setup ---
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# Define authorizations for Swagger UI - Simple static token check
authorizations = {
    'AdminToken': {
        'type': 'apiKey',
        'in': 'header',
        'name': 'X-Admin-Token' # Use a custom header for the static token
    }
}

api = Api(
    admin_bp,
    version='1.0',
    title='Madrassati Admin API',
    description='API endpoints for managing Madrassati administration tasks.',
    doc='/doc/', # URL for Swagger UI documentation
    authorizations=authorizations, # Add authorization info
    security='AdminToken' # Apply default security requirement to all endpoints in this API
)

# --- Namespace Definition ---
# All routes in this module will be under this namespace
admin_ns = api.namespace('manage', description='Admin Management Operations')

# --- Error Handling for the Namespace ---
from .errors import AdminError
from flask import jsonify

@admin_ns.errorhandler(AdminError)
def handle_admin_error(error):
    """Custom error handler for AdminError subclasses."""
    return {'error': error.message}, error.status_code

@admin_ns.errorhandler(Exception)
def handle_generic_error(error):
    """Generic error handler for unexpected errors."""
    # Log the full error for debugging
    current_app.logger.error(f"Unhandled exception in admin namespace: {error}", exc_info=True)
    # Return a generic message
    return {'error': 'An unexpected internal server error occurred.'}, 500


# --- Simple Admin Auth Decorator ---
from functools import wraps
from flask import request

def admin_required(f):
    """Simple decorator to check for the static admin token."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get('X-Admin-Token')
        if not token or token != ADMIN_STATIC_TOKEN:
            # Use the custom AdminAuthError
            from .errors import AdminAuthError
            raise AdminAuthError("Admin access required.")
        return f(*args, **kwargs)
    return decorated_function


# Import routes after defining blueprint, api, namespace, and decorator
# to avoid circular imports
from . import routes
