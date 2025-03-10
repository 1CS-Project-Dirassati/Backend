from flask import  request, jsonify
from . import auth_bp
import jwt
import datetime
from werkzeug.security import check_password_hash, generate_password_hash
from madrassati.config import Config
from madrassati.models import User  # Assuming a SQLAlchemy model
from madrassati.extensions import db


def generate_token(user_id):
    """Generate a JWT token."""
    payload = {
        "user_id": user_id,
        "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=Config.JWT_EXPIRATION),
        "iat": datetime.datetime.now(datetime.timezone.utc),
    }
    return jwt.encode(payload, Config.SECRET_KEY, algorithm=Config.JWT_ALGORITHM)

@auth_bp.route("/login", methods=["POST"])
def login():
    """Authenticate user and return a JWT token."""
    data = request.get_json()


    username = data.get("username")
    password = data.get("password")

    user = User.query.filter_by(username=username).first()


    if not user:
        return jsonify({"error": "Invalid credentials"}), 401
    
    if not check_password_hash(user.password, password):
        return jsonify({"error": "Invalid credentials"}), 401


    # Generate JWT token
    token = generate_token(user.id)

    return jsonify({"token": token, "message": "Login successful"}), 200




@auth_bp.route("/register", methods=["POST"])
def register():
    """Register a new user."""
    data = request.get_json()

    # Extract and validate input
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({"error": "Username and password are required"}), 400

    # Check if user already exists
    existing_user = User.query.filter_by(username=username).first()
    if existing_user:
        return jsonify({"error": "User already exists"}), 409


    new_user = User(username=username, password=password)
    db.session.add(new_user)
    db.session.commit()

    return jsonify({"message": "User registered successfully"}), 201