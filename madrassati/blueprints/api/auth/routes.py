# madrassati/auth/routes.py
from flask import request
from flask_restx import Resource , fields , reqparse
from madrassati.extensions import flask_limiter
#import the auth namespace
from . import auth_ns
#import business logic
from .views import (
    login,
    initiate_registration,
    complete_registration,
    refresh_token,
    request_password_reset,
    reset_password_with_otp
)
    #import errors
from .errors import AuthError, MissingDataError # Import base and specific errors

# define data models for request and response marshaling and documentation
# generic message model
message_model = auth_ns.model("MessageModel", {
    "message": fields.String(description="Message", required=True)
})
# generic error models
error_model = auth_ns.model("ErrorModel", {
    "error": fields.String(description="Error message", required=True)
})
# login payload model
login_payload_model = auth_ns.model("LoginPayload", {
    "email": fields.String(description="User email", required=True),
    "password": fields.String(description="User password", required=True)
})
# login response model
token_model = auth_ns.model("TokenModel", {
    "message": fields.String(description="Message", required=True),
    "access-token": fields.String(description="access token (to be saved in local storage)", required=True),
    "refresh-token": fields.String(description="refresh token (to be saved in secure storage/http cookie)", required=True),
})
# token refresh payload model
token_refresh_payload_model = auth_ns.model("TokenRefreshPayload", {
    "refresh-token": fields.String(description="refresh token",required=True),
})
# token refresh response model
token_refresh_response_model = auth_ns.model("TokenRefreshResponse", {
    "message": fields.String(description="Message", required=True),
    "access-token": fields.String(description="access token (to be saved in local storage)", required=True),
})

# registration payload model
register_payload_model = auth_ns.model("RegisterPayload", {
    "email": fields.String(description="User email", required=True),
    "password": fields.String(description="User password", required=True),
    "phoneNumber": fields.String(description="User phone number", required=True)
})

# OTP verification payload model
verify_otp_payload_model = auth_ns.model("VerifyOtpPayload", {
    "email": fields.String(description="User email", required=True),
    "phoneNumber": fields.String(description="User phone number", required=True),
    "otp": fields.String(description="One-Time Password", required=True),
    "password": fields.String(description="User password", required=True)
})
forgot_password_payload_model = auth_ns.model("ForgotPasswordPayload", {
    "phoneNumber": fields.String(description="User phone number", required=True)
})
reset_password_payload_model = auth_ns.model("ResetPasswordPayload", {
    "phoneNumber": fields.String(description="User phone number", required=True),
    "otp": fields.String(description="One-Time Password", required=True),
    "password": fields.String(description="New password", required=True)
})
@auth_ns.errorhandler(AuthError)
def handle_auth_exceptions(error):
    """Custom error handler for AuthError subclasses within this namespace."""
    return {'error': str(error)}, error.status_code

# --- Resources ---
@auth_ns.route('/login')
class LoginResource(Resource):
    method_decorators = [flask_limiter.limit("5 per minute")]
    @auth_ns.doc('user_login', description='Authenticate a user and receive an access and refresh token.')
    @auth_ns.expect(login_payload_model, validate=True)
    @auth_ns.response(200, 'Login successful', token_model)
    @auth_ns.response(400, 'Invalid input data', error_model)
    @auth_ns.response(401, 'Invalid credentials', error_model)
    def post(self):
        """Handles user login."""
        # data = login_parser.parse_args() # Option 1
        data = auth_ns.payload # Option 2: gets validated data from expect(model)
        try:
            # Call the business logic function from views.py
            result = login(data['email'], data['password'])
            return result, 200 # RESTX automatically marshals based on response decorator
        except AuthError as e:
             # Let the namespace error handler catch this
             raise e
        except Exception as e:
             # Catch unexpected errors
             auth_ns.abort(500, f"An unexpected error occurred: {e}")

@auth_ns.route('/refresh-token')
class RefreshTokenResource(Resource):
    method_decorators = [flask_limiter.limit("5 per minute")]
    @auth_ns.doc('refresh_token', description='Refresh the access token using the refresh token.')
    @auth_ns.expect(token_refresh_payload_model, validate=True)
    @auth_ns.response(200, 'Token refreshed successfully', token_refresh_response_model)
    @auth_ns.response(400, 'Invalid input data', error_model)
    @auth_ns.response(406, 'Invalid or expired refresh token', error_model)
    def post(self):
        """handles refreshing the access token."""
        data = auth_ns.payload
        try:
            result = refresh_token (data['refresh-token'])
            return result, 200
        except AuthError as e:
            raise e
        except Exception as e:
             auth_ns.abort(500, f"An unexpected error occurred: {e}")
@auth_ns.route('/register')
class RegisterResource(Resource):
    method_decorators = [flask_limiter.limit("3 per minute")]

    @auth_ns.doc('user_register', description='Initiate user registration by sending an OTP.')
    @auth_ns.expect(register_payload_model, validate=True)
    @auth_ns.response(201, 'OTP sent successfully', message_model) # 201 Created or 202 Accepted
    @auth_ns.response(400, 'Invalid input data', error_model)
    @auth_ns.response(409, 'User already exists', error_model)
    def post(self):
        """Handles initiating user registration."""
        data = auth_ns.payload
        try:
            result = initiate_registration(data['email'], data['password'], data['phoneNumber'])
            # Note: The original returned OTP in message. This is insecure.
            # Returning a generic success message is better.
            # Adjust `initiate_registration` if needed or just return standard message here.
            # return {"message": "OTP sent successfully. Please verify."}, 201
            return result, 201 # If initiate_registration returns the required dict
        except AuthError as e:
            raise e
        except Exception as e:
             auth_ns.abort(500, f"An unexpected error occurred: {e}")

@auth_ns.route('/verify-otp')
class VerifyOtpResource(Resource):
    method_decorators = [flask_limiter.limit("5 per minute")]

    @auth_ns.doc('verify_registration_otp', description='Verify OTP to complete user registration.')
    @auth_ns.expect(verify_otp_payload_model, validate=True)
    @auth_ns.response(201, 'Registration completed successfully', message_model)
    @auth_ns.response(400, 'Invalid input data', error_model)
    @auth_ns.response(403, 'Invalid or expired OTP', error_model)
    def post(self):
        """Handles OTP verification for registration."""
        data = auth_ns.payload
        try:
            result = complete_registration(data['email'], data['phoneNumber'], data['otp'], data['password'])
            return result, 201
        except AuthError as e:
            raise e
        except Exception as e:
             auth_ns.abort(500, f"An unexpected error occurred: {e}")


@auth_ns.route('/forgot-password')
class ForgotPasswordResource(Resource):
    method_decorators = [flask_limiter.limit("3 per minute")]

    @auth_ns.doc('forgot_password_request', description='Request an OTP to reset password.')
    @auth_ns.expect(forgot_password_payload_model, validate=True)
    @auth_ns.response(200, 'OTP sent for password reset', message_model)
    @auth_ns.response(400, 'Invalid input data', error_model)
    @auth_ns.response(404, 'User not found', error_model)
    def post(self):
        """Handles request for password reset OTP."""
        data = auth_ns.payload
        try:
            result = request_password_reset(data['phoneNumber'])
            return result, 200
        except AuthError as e:
            raise e
        except Exception as e:
             auth_ns.abort(500, f"An unexpected error occurred: {e}")


@auth_ns.route('/verify-otp-reset')
class VerifyOtpResetResource(Resource):
    method_decorators = [flask_limiter.limit("5 per minute")]

    @auth_ns.doc('verify_reset_otp', description='Verify OTP and set a new password.')
    @auth_ns.expect(reset_password_payload_model, validate=True)
    @auth_ns.response(200, 'Password reset successful', message_model)
    @auth_ns.response(400, 'Invalid input data', error_model)
    @auth_ns.response(403, 'Invalid or expired OTP', error_model)
    @auth_ns.response(404, 'User not found', error_model)
    def post(self):
        """Handles OTP verification and password reset."""
        data = auth_ns.payload
        try:
            result = reset_password_with_otp(data['phoneNumber'], data['otp'], data['password'])
            return result, 200
        except AuthError as e:
            raise e
        except Exception as e:
             auth_ns.abort(500, f"An unexpected error occurred: {e}")
