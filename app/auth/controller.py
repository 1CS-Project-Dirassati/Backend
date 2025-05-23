from flask import request
import logging
from flask_restx import Resource
from app.extensions import limiter

# Ensure validation_error is correctly implemented in app.utils
from app.utils import validation_error
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt

# Auth modules
from .service import AuthService
from .dto import AuthDto

# Added ResetPasswordSchema, fixed ForgotSchema import if needed
from .utils import (
    LoginSchema,
    LogoutSchema,
    RefreshSchema,
    RegisterSchema,
    OtpSchema,
    ForgotSchema,
    ResetPasswordSchema,
)

logging.basicConfig(
    level=logging.DEBUG,  # Change to INFO or WARNING in production
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
# Removed global ACCESS_EXPIRES, should be handled by service/config

api = AuthDto.api
auth_success = AuthDto.auth_success  # Generic success DTO
auth_login_success = (
    AuthDto.auth_success
)  # Use specific DTO if response structure differs

login_schema = LoginSchema()
register_schema = RegisterSchema()
refresh_schema = RefreshSchema()  # Not used for validation if only header
otp_schema = OtpSchema()
logout_schema = LogoutSchema()  # Not used for validation if only header
forgot_schema = ForgotSchema()
reset_password_schema = ResetPasswordSchema()  # Instantiate new schema


@api.route("/login")
class AuthLogin(Resource):
    """User login endpoint"""

    auth_login_req = AuthDto.auth_login
    auth_login_resp = AuthDto.auth_success  # Or a specific login response DTO

    @limiter.limit("5 per minute")  # Rate limit for login attempts
    @api.doc(
        "Auth login",
        responses={
            200: ("Logged in successfully", auth_login_resp),
            400: "Validation errors.",
            401: "Incorrect password or role.",  # 401 more standard for auth failures
            404: "Email does not match any account.",
        },
    )
    @api.expect(auth_login_req, validate=True)
    def post(self):
        """Login using email, password, and role"""
        login_data = request.get_json()
        if errors := login_schema.validate(login_data):
            return validation_error(False, errors), 400
        return AuthService.login(login_data)


@api.route("/logout")
class AuthLogout(Resource):
    """User logout endpoint (revokes current token)"""

    # No request body expected if using @jwt_required
    # auth_logout_req = AuthDto.auth_logout
    auth_logout_resp = AuthDto.auth_success  # Generic success message

    @limiter.limit("300 per minute")  # Rate limit for logout attempts
    @api.doc(
        "Auth logout",
        security="Bearer",  # Indicate JWT Bearer token is required
        responses={
            200: ("Successfully logged out.", auth_logout_resp),
            401: "Missing or invalid Authorization Token.",  # From @jwt_required
            500: "Logout failed due to internal issue.",
        },
    )
    # No @api.expect needed if no body is expected
    # @api.expect(auth_logout_req, validate=False)
    @jwt_required(
        verify_type=False
    )  # Allows both access/refresh tokens. Consider separate endpoints?
    def delete(self):
        """Revoke the token used for this request"""
        token = get_jwt()  # Get the decoded token payload
        # Validation of header/token structure is handled by @jwt_required
        return AuthService.logout(token)


@api.route("/register")
class AuthRegister(Resource):
    """User register endpoint"""

    auth_register_req = AuthDto.auth_register
    auth_register_resp = AuthDto.auth_success  # Response includes tokens and user

    @limiter.limit("300 per minute")  # Rate limit for registration attempts
    @api.doc(
        "Auth registration",
        responses={
            201: (
                "OTP sent for verification.",
                auth_register_resp,
            ),  # OTP sent, user not fully created yet
            400: "Malformed data or validations failed.",
            403: "Admin registration forbidden.",
            409: "Email is already registered.",  # Use 409 Conflict
            429: "OTP already sent recently.",
        },
    )
    @api.expect(auth_register_req, validate=True)
    def post(self):
        """User registration - Triggers OTP"""
        register_data = request.get_json()
        if errors := register_schema.validate(register_data):
            return validation_error(False, errors), 400
        return AuthService.register(register_data)


@api.route("/verify-otp")
class AuthVerifyOtp(Resource):
    """User verify OTP endpoint (for registration)"""

    auth_verify_otp_req = AuthDto.auth_verify_otp
    auth_verify_otp_resp = AuthDto.auth_success  # Includes tokens and user

    @limiter.limit("5 per hour")  # Rate limit for OTP verification attempts
    @api.doc(
        "Auth verify OTP",
        responses={
            201: (
                "Successfully verified OTP and registered user.",
                auth_verify_otp_resp,
            ),
            400: "Malformed data, validations failed, or invalid OTP.",
            409: "Email was registered concurrently.",
            500: "Internal state error or DB error.",
        },
    )
    @api.expect(auth_verify_otp_req, validate=True)
    def post(self):
        """Verify OTP sent during registration"""
        otp_data = request.get_json()
        if errors := otp_schema.validate(otp_data):
            return validation_error(False, errors), 400
        return AuthService.verify_otp(otp_data)


@api.route("/forgot-password")
class AuthForgotPassword(Resource):
    """User forgot password endpoint"""

    auth_forgot_req = AuthDto.auth_forgot
    auth_forgot_resp = AuthDto.auth_success  # Only status and message

    @limiter.limit("3 per hour")  # Rate limit for password reset requests
    @api.doc(
        "Auth forgot password",
        responses={
            # Always return 200 OK to prevent email enumeration
            200: (
                "Password reset instructions sent if account exists.",
                auth_forgot_resp,
            ),
            400: "Malformed data or validations failed.",
            500: "Internal server error (e.g., config missing).",
        },
    )
    @api.expect(auth_forgot_req, validate=True)
    def post(self):
        """Request password reset link"""
        forgot_data = request.get_json()
        if errors := forgot_schema.validate(forgot_data):
            return validation_error(False, errors), 400
        # Service layer handles logic and always returns success message publicly
        return AuthService.forgot_password(forgot_data)


# ---- NEW ENDPOINT ----
@api.route("/reset-password")
class AuthResetPassword(Resource):
    """User reset password endpoint"""

    auth_reset_req = AuthDto.auth_reset_password
    auth_reset_resp = AuthDto.auth_success  # Only status and message

    @limiter.limit("5 per hour")  # Rate limit for password reset attempts
    @api.doc(
        "Auth reset password",
        responses={
            200: ("Password successfully reset.", auth_reset_resp),
            400: (
                "Validation errors, invalid/expired token, "
                "or corrupted token payload."
            ),
            404: "User associated with token not found.",
            500: "Internal server error.",
        },
    )
    @api.expect(auth_reset_req, validate=True)
    def post(self):
        """Reset password using token and new password"""
        reset_data = request.get_json()
        if errors := reset_password_schema.validate(reset_data):
            return validation_error(False, errors), 400
        return AuthService.reset_password(reset_data)


@api.route("/refresh")
class AuthRefresh(Resource):
    """User refresh token endpoint"""

    auth_refresh_req = AuthDto.auth_refresh  # Empty model
    auth_refresh_resp = AuthDto.auth_success  # Returns new access token

    @limiter.limit("30 per minute")  # Rate limit for refresh attempts
    @api.doc(
        "Auth refresh access token",
        security="Bearer",  # Requires Bearer refresh token
        responses={
            200: ("Successfully refreshed access token.", auth_refresh_resp),
            401: "Missing, invalid, or expired refresh token.",  # From @jwt_required
            500: "Internal server error.",
        },
    )
    @api.expect(auth_refresh_req, validate=False)  # No body expected
    @jwt_required(refresh=True)  # Ensures it's a valid refresh token
    def post(self):
        """Refresh access token using Bearer refresh token"""
        print("identity gotten from refresh token")
        identity = get_jwt_identity()  # Get identity from refresh token
        role = get_jwt()["role"]
        print(identity)
        return AuthService.refresh(identity, role)
