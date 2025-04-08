# madrassati/auth/views.py
from werkzeug.security import generate_password_hash, check_password_hash

from madrassati.models import User
from madrassati.extensions import db
from .utils import generate_token, generate_and_store_otp, verify_stored_otp
from .errors import InvalidCredentialsError, UserNotFoundError, UserAlreadyExistsError, InvalidOtpError # Assuming you create these custom exceptions in errors.py

def login_user(email, password):
    """
    Authenticates a user based on email and password.

    Args:
        email (str): User's email.
        password (str): User's password.

    Returns:
        dict: Dictionary containing the JWT token.

    Raises:
        InvalidCredentialsError: If email/password combination is incorrect.
    """
    user = User.query.filter_by(email=email).first()
    if not user or not check_password_hash(user.password, password):
        raise InvalidCredentialsError("Invalid email or password")

    token = generate_token(user.id)
    return {"token": token}


def initiate_registration(email, password, phone_number):
    """
    Initiates the registration process by checking for existing users and sending an OTP.

    Args:
        email (str): User's desired email.
        password (str): User's desired password (will be needed later).
        phone_number (str): User's phone number for OTP verification.

    Returns:
        dict: Success message indicating OTP was sent.

    Raises:
        UserAlreadyExistsError: If a user with the given email already exists.
    """
    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        raise UserAlreadyExistsError("User with this email already exists")

    # Note: Password isn't used here but passed to keep track for the next step (verify_otp)
    # In a real scenario, you might store temporary registration data linked to the OTP.
    otp_code = generate_and_store_otp(phone_number)

    # NOTE: Returning OTP in message only for consistency with original code.
    # In production, DO NOT return the OTP code in the response.
    return {"message": f"OTP sent successfully:otp:{otp_code}. Please verify to complete registration."}


def complete_registration(email, phone_number, otp_code, password):
    """
    Verifies the OTP and completes the user registration.

    Args:
        email (str): User's email.
        phone_number (str): User's phone number.
        otp_code (str): The OTP submitted by the user.
        password (str): The user's desired password.

    Returns:
        dict: Success message indicating registration is complete.

    Raises:
        InvalidOtpError: If the provided OTP is invalid or expired.
    """
    if not verify_stored_otp(phone_number, otp_code):
        raise InvalidOtpError("Invalid or expired OTP")

    # OTP verified, now create the user
    hashed_password = generate_password_hash(password)
    new_user = User(email=email, phoneNumber=phone_number, password=hashed_password)
    db.session.add(new_user)
    db.session.commit()

    return {"message": "Registration completed successfully."}


def request_password_reset(phone_number):
    """
    Initiates the password reset process by sending an OTP to the user's phone number.

    Args:
        phone_number (str): The user's phone number.

    Returns:
        dict: Success message indicating OTP was sent.

    Raises:
        UserNotFoundError: If no user is found with the given phone number.
    """
    user = User.query.filter_by(phoneNumber=phone_number).first()
    if not user:
        raise UserNotFoundError("User with this phone number not found.")

    otp = generate_and_store_otp(phone_number) # OTP is generated and stored

    return {"message": f"OTP sent:otp:{otp}. Please verify to reset password."}


def reset_password_with_otp(phone_number, otp_code, new_password):
    """
    Verifies the OTP and resets the user's password.

    Args:
        phone_number (str): The user's phone number.
        otp_code (str): The OTP submitted by the user.
        new_password (str): The new password for the user.

    Returns:
        dict: Success message indicating the password was reset.

    Raises:
        InvalidOtpError: If the provided OTP is invalid or expired.
        UserNotFoundError: If no user is found with the given phone number (should be rare here if OTP was valid).
    """
    if not verify_stored_otp(phone_number, otp_code):
        raise InvalidOtpError("Invalid or expired OTP")

    user = User.query.filter_by(phoneNumber=phone_number).first()
    # This check is slightly redundant if verify_stored_otp requires the user exists implicitly,
    # but good practice to ensure the user exists before updating.
    if not user:
        # Should ideally not happen if OTP verification passed, unless user deleted between steps.
        raise UserNotFoundError("User not found during password update.")

    user.password = generate_password_hash(new_password)
    db.session.commit()

    return {"message": "Password reset successful."}
