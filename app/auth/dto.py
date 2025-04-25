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
            "name": fields.String,
            "username": fields.String,
            "joined_date": fields.DateTime,
            "role_id": fields.Integer,
        },
    )

    auth_login = api.model(
        "Login data",
        {
            "email": fields.String(required=True, example="johndoe@martello.com"),
            "password": fields.String(required=True, example="supersecretpassword"),
            "role": fields.String(
                required=True,
                enum=["parent", "teacher", "admin", "student"],
                description="Role of the user",
            ),
        },
    )
    auth_refresh = api.model(
        "Refresh token",
        {},
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
                description="Phone number of the user",
                example="+1234567890",
            ),
            "first_name": fields.String(example="John"),
            "last_name": fields.String(example="Doe"),
        },
    )
    auth_verify_otp = api.model(
        "Verify OTP",
        {
            "otp": fields.String(required=True, example="123456"),
            "email": fields.String(required=True, example="jane@jane.com"),
        },
    )

    auth_success = api.model(
        "Auth success response",
        {
            "status": fields.Boolean,
            "message": fields.String,
            "access_token": fields.String,
            "user": fields.Nested(user_obj),
        },
    )
