from flask import request
import logging
from flask_restx import Resource
from app.utils import validation_error
from flask_jwt_extended import jwt_required, get_jwt_identity

# Auth modules
from .service import AuthService
from .dto import AuthDto
from .utils import LoginSchema, RefreshSchema, RegisterSchema, OtpSchema

logging.basicConfig(
    level=logging.DEBUG,  # Change to INFO or WARNING in production
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

api = AuthDto.api
auth_success = AuthDto.auth_success

login_schema = LoginSchema()
register_schema = RegisterSchema()
refresh_schema = RefreshSchema()
otp_schema = OtpSchema()


@api.route("/login")
class AuthLogin(Resource):
    """User login endpoint
    User registers then receives the user's information and access_token
    """

    auth_login = AuthDto.auth_login

    @api.doc(
        "Auth login",
        responses={
            200: ("Logged in", auth_success),
            400: "Validations failed.",
            403: "Incorrect password or incomplete credentials.",
            404: "Email does not match any account.",
        },
    )
    @api.expect(auth_login, validate=True)
    def post(self):
        """Login using email and password"""
        # Grab the json data
        login_data = request.get_json()
        # Validate data
        if errors := login_schema.validate(login_data):
            return validation_error(False, errors), 400

        return AuthService.login(login_data)


@api.route("/register")
class AuthRegister(Resource):
    """User register endpoint
    User registers then receives the user's information and access_token
    """

    auth_register = AuthDto.auth_register

    @api.doc(
        "Auth registration",
        responses={
            201: ("Successfully registered user.", auth_success),
            400: "Malformed data or validations failed.",
        },
    )
    @api.expect(auth_register, validate=True)
    def post(self):
        """User registration"""
        # Grab the json data
        register_data = request.get_json()

        # Validate data
        if errors := register_schema.validate(register_data):
            return validation_error(False, errors), 400

        return AuthService.register(register_data)


@api.route("/verify-otp")
class AuthVerifyOtp(Resource):
    """User verify OTP endpoint
    User verifies the OTP sent to their email
    """

    auth_verify_otp = AuthDto.auth_verify_otp

    @api.doc(
        "Auth verify OTP",
        responses={
            200: ("Successfully verified OTP.", auth_success),
            400: "Malformed data or validations failed.",
            401: "Invalid token.",
        },
    )
    @api.expect(auth_verify_otp, validate=True)
    def post(self):
        """Verify OTP"""
        # Grab the json data

        otp_data = request.get_json()
        # Validate otp_data
        if errors := otp_schema.validate(otp_data):
            return validation_error(False, errors), 400
        return AuthService.verify_otp(otp_data)


@api.route("/refresh")
class AuthRefresh(Resource):
    """User refresh token endpoint
    User refreshes the access token using the refresh token
    """

    auth_refresh = AuthDto.auth_refresh

    @api.doc(
        "Auth refresh",
        responses={
            200: ("Successfully refreshed token.", auth_success),
            400: "Malformed data or validations failed.",
            401: "Invalid token.",
        },
    )
    @api.expect(auth_refresh, validate=False)
    @api.doc(security="Bearer")
    @jwt_required(refresh=True)
    def post(self):
        """Refresh access token"""
        # Grab the json data
        identity = get_jwt_identity()

        return AuthService.refresh(identity)
