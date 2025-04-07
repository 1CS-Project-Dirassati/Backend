from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timezone, timedelta
import random
import jwt
from madrassati.config import Config
from madrassati.models import Parent, User
from madrassati.extensions import db, redis_client
from madrassati.extensions import flask_limiter
from flask_limiter.util import get_remote_address
from . import auth_bp

# OTP expiration time (in minutes)
OTP_EXPIRATION_MINUTES = 10


def generate_token(user_id):
    """Generate a JWT token."""
    payload = {
        "user_id": user_id,
        "exp": datetime.now(timezone.utc) + timedelta(seconds=Config.JWT_EXPIRATION),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, Config.SECRET_KEY, algorithm=Config.JWT_ALGORITHM)


@auth_bp.route("/login", methods=["POST"])
@flask_limiter.limit("5 per minute")  # Limit to 5 login attempts per minute per IP
def login():
    """Authenticate user and return a JWT token."""
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")

    user = User.query.filter_by(email=email).first()
    if not user or not check_password_hash(user.password, password):
        return jsonify({"error": "Invalid credentials"}), 401

    # Generate JWT token
    token = generate_token(user.id)

    return jsonify({"token": token, "message": "Login successful"}), 200


@auth_bp.route("/register", methods=["POST"])
@flask_limiter.limit("3 per minute")  # Limit to 3 registrations per minute per IP
def register():
    """Register a new user."""
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")
    phone_number = data.get("phoneNumber")

    if not email or not password or not phone_number:
        return jsonify({"error": "Email, password, and phone number are required"}), 400

    # Check if user already exists
    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        return jsonify({"error": "User already exists"}), 409

    # Generate a 5-digit random OTP
    otp_code = random.randint(10000, 99999)

    print (otp_code)
    expiration_time = timedelta(minutes=OTP_EXPIRATION_MINUTES)

    # Store OTP in Redis with expiration time
    redis_client.setex(f"otp:{phone_number}", expiration_time, otp_code)

    # Print OTP for debugging (remove in production)
    print(f"OTP for {phone_number}: {otp_code}")

    return jsonify({"message": f"OTP sent successfully:otp:{otp_code}. Please verify to complete registration."}), 201


@auth_bp.route("/verify-otp", methods=["POST"])
@flask_limiter.limit("5 per minute")  # Limit OTP verification attempts
def verify_otp():
    """Verify OTP and complete registration."""
    data = request.get_json()
    email = data.get("email")
    phone_number = data.get("phoneNumber")
    otp_code = data.get("otp")
    password = data.get("password")

    if not email or not phone_number or not otp_code or not password:
        return jsonify({"error": "Missing required fields"}), 400
    # Retrieve OTP from Redis
    stored_otp = redis_client.get(f"otp:{phone_number}")
    string_otp = stored_otp.decode() if isinstance(stored_otp, bytes) else str(stored_otp)

    if not stored_otp or string_otp != otp_code:
        return jsonify({"error": "Invalid or expired OTP"}), 403

    # Remove OTP after successful verification
    redis_client.delete(f"otp:{phone_number}")


    # Create and save user
    new_user = User(email=email, phoneNumber=phone_number, password=generate_password_hash(password))
    db.session.add(new_user)
    db.session.commit()

    return jsonify({"message": "Registration completed successfully."}), 201
@auth_bp.route("/forgot-password", methods=["POST"])
@flask_limiter.limit("3 per minute")
def forgot_password():
    """Send an OTP for password reset via phone number."""
    data = request.get_json()
    phone_number = data.get("phoneNumber")

    user = User.query.filter_by(phoneNumber=phone_number).first()
    if not user:
        return jsonify({"error": "User not found."}), 404

    # Generate a new OTP
    otp_code = random.randint(10000, 99999)
    expiration_time = timedelta(minutes=OTP_EXPIRATION_MINUTES)
    print (otp_code)

    # Store OTP in Redis
    redis_client.setex(f"otp:{phone_number}", expiration_time, otp_code)

    # TODO: Send OTP via SMS (replace this with actual SMS API)
    print(f"Password reset OTP for {phone_number}: {otp_code}")

    return jsonify({"message": "OTP sent. Please verify to reset password."}), 200


@auth_bp.route("/verify-otp-reset", methods=["POST"])
@flask_limiter.limit("5 per minute")
def verify_otp_reset():
    """Verify OTP and reset password."""
    data = request.get_json()
    phone_number = data.get("phoneNumber")
    otp_code = data.get("otp")
    new_password = data.get("password")

    if not phone_number or not otp_code or not new_password:
        return jsonify({"error": "Missing required fields"}), 400

    # Retrieve stored OTP from Redis
    stored_otp = redis_client.get(f"otp:{phone_number}")
    string_otp = stored_otp.decode() if isinstance(stored_otp, bytes) else str(stored_otp)

    if not stored_otp or string_otp != otp_code:
        return jsonify({"error": "Invalid or expired OTP"}), 403

    # Remove OTP after successful verification
    redis_client.delete(f"otp:{phone_number}")

    # Update user password
    user = User.query.filter_by(phoneNumber=phone_number).first()
    if not user:
        return jsonify({"error": "User not found."}), 404

    user.password = generate_password_hash(new_password)
    db.session.commit()

    return jsonify({"message": "Password reset successful."}), 200

