# madrassati/auth/views.py
from werkzeug.security import  generate_password_hash, check_password_hash
from datetime import  datetime ,timezone , timedelta
from flask import current_app

from madrassati.models import User
from madrassati.extensions import db , redis_client
from .utils import find_user_by_email,retrieve_token, generate_access_token,generate_refresh_token, generate_and_store_otp, store_token, verify_stored_otp , OTP_EXPIRATION_MINUTES , find_user_by_email
from madrassati.services import send_email
from .errors import MissingDataError, InvalidCredentialsError, InvalidRefreshTokenError, UserNotFoundError, UserAlreadyExistsError, InvalidOtpError # Assuming you create these custom exceptions in errors.py

def login(email, password):
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
    user = find_user_by_email(email)
    if not user or not check_password_hash(user.password, password):
        raise InvalidCredentialsError("Invalid email or password")
    try:
            # Define access token payload
            access_token = generate_access_token(user.id) # Generate access token
            expires_at = datetime.now(timezone.utc) + timedelta(seconds= current_app.config['REFRESH_TOKEN_EXPIRES'])

            # Generate refresh token
            refresh_token = generate_refresh_token()
            # store the refresh token securely
            store_token(user.id , refresh_token, expires_at)
            # Store the refresh token (in a real app, store securely in a database)
            # Return both tokens to the client
            return ({
                "message": "Login successful",
                "access_token": access_token,
                "refresh_token": refresh_token
                # Optionally include basic user info again
                # "user": {"id": user['id'], "email": user['email']}
            }), 200 # OK

    except Exception as e:
            current_app.logger.error(f"Error generating tokens: {e}")
            return ({"error": "Failed to generate authentication tokens"}), 500 # Internal Server Error

def refresh_token(refresh_token):
    """
    Endpoint to refresh the access token using a valid refresh token.
    Expects JSON body with 'refresh_token'.
    Returns a new access token if the refresh token is valid.
    """
    try:
        if not refresh_token:
            raise MissingDataError
        token_dict= retrieve_token(refresh_token)
        if not token_dict:
            raise InvalidRefreshTokenError("dict was empty ")
        print("debug point")
        print(token_dict.get("user_id"))
        print (token_dict.get("expires_at"))
        user_id = token_dict.get("user_id")
        if user_id :
            user = User.query.filter_by(id=user_id).first()
            print(user)
            if user :
                # generate new access token
                access_token = generate_access_token(user.id)
                return ({"access_token": access_token}), 200
            else :
                current_app.logger.warning(f"User not found for user ID from valid refresh token: {user_id}")
                raise InvalidRefreshTokenError("Invalid refresh token")
        else :
            raise InvalidRefreshTokenError("Invalid refresh token")


    except Exception as e:
        current_app.logger.error(f"Error refreshing token: {e}")
        return ({"error": "Failed to refresh token"}), 500

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

    otp_code = generate_and_store_otp(phone_number) # OTP stored in Redis (keyed by phone)

    # --- Send OTP Email ---
    subject = f"Madrassati Registration - Your OTP Code ({otp_code})" # Include OTP in subject for easy finding
    template = "email/otp_email" # Prefix for otp_email.html / otp_email.txt
    context = {
        "otp_code": otp_code,
        "expiration_minutes": OTP_EXPIRATION_MINUTES
    }
    email_sent = send_email(to_email=email, subject=subject, template_prefix=template, context=context)
    if not email_sent:
        # Log the failure but proceed with registration initiation
        # The user can still verify via phone OTP stored in Redis
        current_app.logger.warning(f"Failed to send OTP email to {email} during registration initiation.")
    # --- End Send Email ---

    # Modify the response message - DO NOT include OTP here for security.
    return {"message": "OTP sent to your phone (and email if configured). Please verify to complete registration."}

# --- complete_registration function remains the same ---
# (It only verifies the OTP provided by the user, doesn't send email)
# ...

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
