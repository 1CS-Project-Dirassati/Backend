from flask_restx import Namespace, fields


class AuthDto:
    api = Namespace(
        "auth",
        description="Authenticate and receive tokens.",
        path="/auth",
    )

    user_obj = api.model(
        "User object",
        {
            "email": fields.String,
            "name": fields.String,  # Consider combining first/last or adjusting model
            "username": fields.String,
            "joined_date": fields.DateTime,
            "role_id": fields.Integer,  # Or maybe role name 'role': fields.String
            # Add other relevant non-sensitive user fields if needed
        },
    )
    auth_refresh = api.model(
        "Refresh token request body",
        {},  # Empty as token is in header
        description="No request body needed. Send refresh token in Authorization header (Bearer).",
    )

    auth_login = api.model(
        "Login data",
        {
            "email": fields.String(required=True, example="gulag@maserati.com"),
            "password": fields.String(required=True, example="supersecretpassword"),
            "role": fields.String(
                required=True,
                enum=["parent", "teacher", "admin", "student"],
                description="Role of the user",
            ),
        },
    )

    # Fixed syntax error (removed extra closing parenthesis)
    auth_forgot = api.model(
        "Forgot password data",
        {
            "email": fields.String(
                required=True,
                description="Email of the user",
                example="gulag@maserati.com",
            ),
            "role": fields.String(
                required=True,
                enum=["parent", "teacher", "admin", "student"],
                description="Role of the user",
            ),
        },  # Removed extra parenthesis here
    )

    # ---- NEW MODEL ----
    auth_reset_password = api.model(
        "Reset password data",
        {
            "token": fields.String(
                required=True,
                description="The password reset token received via email link.",
                example="eyJhbGciOiJIUzUx...",  # Example token format (will differ for itsdangerous)
            ),
            "new_password": fields.String(
                required=True,
                description="The desired new password (min 8 chars).",
                example="newStrongPassword123",
            ),
        },
    )

    auth_logout = api.model(
        "Logout request body",
        {},  # Empty as token is in header
        description="No request body needed. Send token to revoke in Authorization header (Bearer).",
        # { # Usually not needed if token is from header via @jwt_required
        #     "token": fields.String(
        #         required=True,
        #         description="Refresh/Access token to be revoked",
        #         example="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        #     ),
        # },
    )

    auth_register = api.model(
        "Registration data",
        {
            "email": fields.String(required=True, example="gulag@maserati.com"),
            "password": fields.String(required=True, example="supersecretpassword"),
            "role": fields.String(
                required=True,
                enum=["parent", "teacher", "admin", "student"],
                description="Role of the user",
            ),
            "phone_number": fields.String(
                required=True,
                description="Phone number of the user (E.164 format recommended)",
                example="+1234567890",
            ),
            "first_name": fields.String(required=True, example="John"),
            "last_name": fields.String(required=True, example="Doe"),
        },
    )
    auth_verify_otp = api.model(
        "Verify OTP",
        {
            "otp": fields.String(required=True, example="123456"),
            "email": fields.String(required=True, example="jane@jane.com"),
            # Removed context field, align with OtpSchema or add back if needed
            # "context": fields.String(required=True, example="register"),
        },
    )

    # Added refresh_token and made user optional as it's not always returned
    auth_success = api.model(
        "Auth success response",
        {
            "status": fields.Boolean(default=True),
            "message": fields.String,
            "access_token": fields.String(
                required=False
            ),  # Not returned on all success messages
            "refresh_token": fields.String(
                required=False
            ),  # Returned on login/register
            "user": fields.Nested(
                user_obj, required=False
            ),  # Returned on login/register
        },
    )
