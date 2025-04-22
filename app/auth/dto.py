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
            "email": fields.String(required=True),
            "password": fields.String(required=True),
            "role": fields.String(
                required=True,
                enum=["parent", "teacher", "admin", "student"],
                description="Role of the user",
            ),
        },
    )
    auth_refresh = api.model(
        "Refresh token",
        {
        },
    )

    auth_register = api.model(
        "Registration data",
        {
            "email": fields.String(required=True),
            "role": fields.String(
                required=True,
                enum=["parent", "teacher", "admin", "student"],
                description="Role of the user",
            ),
            # Name is optional
            "name": fields.String,
            "password": fields.String(required=True),
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
