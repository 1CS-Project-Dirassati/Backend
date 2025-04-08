from flask import jsonify

def handle_error(message, status_code):
    """Centralized error handler."""
    return jsonify({"error": message}), status_code
