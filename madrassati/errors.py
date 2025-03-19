from flask import jsonify

def handle_404(error):
    response = jsonify({"error": "Not Found", "message": "The requested resource was not found."})
    response.status_code = 404
    return response

def handle_401(error):
    response = jsonify({"error": "Unauthorized", "message": "Invalid credentials or token."})
    response.status_code = 401
    return response

def handle_500(error):
    response = jsonify({"error": "Server Error", "message": "An internal server error occurred."})
    response.status_code = 500
    return response

